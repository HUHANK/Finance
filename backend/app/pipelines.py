# -*- coding: utf-8 -*-
"""聚合管道：复盘快照、估值/权重入库、联播入库。供 API 与定时任务共用。"""
import datetime
import json
import logging

from . import config, db
from .sources import cctv, csindex, eastmoney, sse, tencent

log = logging.getLogger(__name__)


def today_str():
    return datetime.date.today().strftime("%Y-%m-%d")


# ---------- 复盘快照 ----------

def market_recent(indexes, n=6):
    """指数近 5 个交易日概览（count=6 根 bar，last/bars[0]-1 ≈ 5 日涨幅）。"""
    out = []
    for sym, name in indexes:
        try:
            bars = tencent.kline(sym, period="day", count=n, fq="none")
            if not bars:
                continue
            last = bars[-1]
            chg5 = (last["close"] / bars[0]["close"] - 1) * 100 if len(bars) >= 2 else 0
            out.append({"code": sym, "name": name, "date": last["date"],
                        "close": last["close"], "chg5d": round(chg5, 2)})
        except Exception as e:
            log.warning("market_recent %s failed: %s", sym, e)
    return out


def _store_shares(date_str, code_map):
    db.executemany(
        "INSERT OR REPLACE INTO etf_share(date, code, name, shares) VALUES(?,?,?,?)",
        [(date_str, c, r["name"], r["shares"]) for c, r in code_map.items()])


def _sse_latest_available(start_date, max_back=10):
    """SSE 份额数据发布有延迟（当日通常晚间/次日出）：从 start_date 往前找最近有数据的日期。"""
    d = datetime.date.fromisoformat(start_date)
    for _ in range(max_back):
        s = d.strftime("%Y-%m-%d")
        try:
            return s, sse.etf_shares_sh(s)
        except ValueError:
            d -= datetime.timedelta(days=1)
    raise ValueError("SSE 近 %d 天均无份额数据" % max_back)


def build_etf_delta(date_str, top_n=18):
    """沪市 ETF 份额变动：数据日 vs 库内上一快照日（首次用 ~7 天前）。"""
    cur_date, new_map = _sse_latest_available(date_str)
    prev = db.query("SELECT date FROM etf_share WHERE date<? ORDER BY date DESC LIMIT 1",
                    (cur_date,))
    if prev:
        prev_date = prev[0]["date"]
        prev_map = {r["code"]: r["shares"]
                    for r in db.query("SELECT code, shares FROM etf_share WHERE date=?", (prev_date,))}
    else:
        before = (datetime.date.fromisoformat(cur_date)
                  - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            prev_date, prev_map = _sse_latest_available(before)
            prev_map = {c: r["shares"] for c, r in prev_map.items()}
        except ValueError as e:
            log.warning("prev shares before %s failed: %s", before, e)
            prev_date, prev_map = None, {}
    deltas = []
    for code, rec in new_map.items():
        if code in prev_map:
            d = rec["shares"] - prev_map[code]  # 万份
            if abs(d) > 1:
                deltas.append({"code": code, "name": rec["name"], "d_wan": round(d, 0)})
    deltas.sort(key=lambda x: abs(x["d_wan"]), reverse=True)
    _store_shares(cur_date, new_map)
    top = deltas[:top_n]
    quotes = tencent.tencent_quote([x["code"] for x in top])
    for x in top:
        x["price"] = quotes.get(x["code"], {}).get("price")
        x["amt_yi"] = round(x["d_wan"] * (x["price"] or 0) / 1e4, 1)
    return {"date": cur_date, "prev_date": prev_date,
            "total": len(deltas), "items": top}


def build_review_snapshot(date_str):
    """抓取某交易日的复盘数据并落库。逐块容错；重建时某块失败则保留库内同日旧数据。"""
    ymd = date_str.replace("-", "")
    payload = {"date": date_str, "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}

    payload["market"] = market_recent(config.INDEX_OVERVIEW[:3])
    for key, fetch in (
        ("sentiment", lambda: eastmoney.limit_up_sentiment(ymd)),
        ("board_flow", lambda: {
            "industry": eastmoney.board_fund_flow("industry", "5d", 40),
            "concept": eastmoney.board_fund_flow("concept", "5d", 40),
        }),
        ("etf_delta", lambda: build_etf_delta(date_str)),
    ):
        try:
            payload[key] = fetch()
        except Exception as e:
            log.warning("%s %s failed: %s", key, date_str, e)
            old = get_snapshot(date_str) or {}
            payload[key] = old.get(key)

    db.execute("INSERT OR REPLACE INTO daily_snapshot(date, payload) VALUES(?,?)",
               (date_str, json.dumps(payload, ensure_ascii=False)))
    return payload


def get_snapshot(date_str):
    rows = db.query("SELECT payload FROM daily_snapshot WHERE date=?", (date_str,))
    return json.loads(rows[0]["payload"]) if rows else None


def snapshot_dates():
    return [r["date"] for r in db.query("SELECT date FROM daily_snapshot ORDER BY date DESC")]


# ---------- 估值 / 权重 ----------

def ensure_valuation_history(index_code, force=False):
    """中证官方估值（PE1/PE2/股息率）近期数据入库。每日最多拉一次（xls 全量覆盖）。"""
    today = today_str()
    if not force and db.kv_get("valuation_updated:" + index_code) == today:
        return False
    rows = csindex.index_valuation(index_code)
    if not rows:
        raise RuntimeError("估值历史为空: %s" % index_code)
    db.execute("DELETE FROM valuation_history WHERE index_code=?", (index_code,))
    db.executemany(
        "INSERT OR REPLACE INTO valuation_history(index_code,date,pe_total,pe_calc,dy_total,dy_calc) "
        "VALUES(?,?,?,?,?,?)",
        [(index_code, r["date"], r["pe_total"], r["pe_calc"], r["dy_total"], r["dy_calc"])
         for r in rows])
    db.kv_set("valuation_updated:" + index_code, today)
    return True


def ensure_pe_history(index_code, force=False):
    """官网日频 PE 长序列入库（2011 起，全量合并；每日最多拉一次）。"""
    today = today_str()
    if not force and db.kv_get("pe_history_updated:" + index_code) == today:
        return False
    rows = csindex.index_pe_history(index_code)
    if not rows:
        raise RuntimeError("PE 长序列为空: %s" % index_code)
    db.executemany("INSERT OR REPLACE INTO pe_history(index_code, date, pe) VALUES(?,?,?)",
                   [(index_code, r["date"], r["pe"]) for r in rows])
    db.kv_set("pe_history_updated:" + index_code, today)
    return True


def pe_history_rows(index_code):
    return db.query("SELECT date, pe FROM pe_history WHERE index_code=? AND pe IS NOT NULL "
                    "ORDER BY date", (index_code,))


def valuation_summary(index_code):
    """估值摘要：PE 长序列最新值 + 多窗口百分位；官方 PE1/PE2/股息率近期值。"""
    pe = [(r["date"], r["pe"]) for r in pe_history_rows(index_code)]
    if not pe:
        return None

    def pct_rank(series, value):
        return round(sum(1 for v in series if v < value) / len(series) * 100)

    last_date, last_pe = pe[-1]
    out = {"index": index_code, "date": last_date, "pe_last": last_pe,
           "n_days": len(pe), "start": pe[0][0],
           "pct_all": pct_rank([v for _, v in pe], last_pe)}
    for label, days in (("pct_3y", 750), ("pct_5y", 1250)):
        window = [v for _, v in pe[-days:]]
        out[label] = pct_rank(window, last_pe) if window else None
    try:
        ensure_valuation_history(index_code)
    except Exception as e:
        log.warning("official valuation %s failed: %s", index_code, e)
    recent = db.query("SELECT pe_total, pe_calc, dy_total FROM valuation_history "
                      "WHERE index_code=? ORDER BY date DESC LIMIT 1", (index_code,))
    if recent:
        out["pe1_official"] = recent[0]["pe_total"]
        out["pe2_official"] = recent[0]["pe_calc"]
        out["dy_official"] = recent[0]["dy_total"]
    return out


def ensure_index_weights(index_code, force=False):
    """成份权重（官方月度文件）入库，统一存文件内最新一期。"""
    today = today_str()
    if not force and db.kv_get("weights_updated:" + index_code):
        return False
    rows = csindex.index_weights(index_code)
    if not rows:
        raise RuntimeError("权重为空: %s" % index_code)
    snap_date = max(r["date"] for r in rows)
    db.execute("DELETE FROM index_weights WHERE index_code=?", (index_code,))
    db.executemany(
        "INSERT OR REPLACE INTO index_weights(index_code,date,code,name,weight) VALUES(?,?,?,?,?)",
        [(index_code, snap_date, r["code"], r["name"], r["weight"]) for r in rows])
    db.kv_set("weights_updated:" + index_code, today)
    return True


# ---------- 新闻联播 ----------

def ensure_cctv(date_str, with_content=True):
    """某日联播入库（已有则跳过）。返回是否新增。"""
    if db.query("SELECT idx FROM cctv_news WHERE date=? LIMIT 1", (date_str,)):
        return False
    items = cctv.cctv_news(date_str, with_content=with_content)
    if not items:
        return False
    db.executemany(
        "INSERT OR REPLACE INTO cctv_news(date, idx, title, url, content) VALUES(?,?,?,?,?)",
        [(date_str, i, it["title"], it["url"], it.get("content"))
         for i, it in enumerate(items, 1)])
    return True


def cctv_dates():
    return [r["date"] for r in db.query("SELECT DISTINCT date FROM cctv_news ORDER BY date DESC")]


def cctv_items(date_str):
    rows = db.query("SELECT idx, title, url, content FROM cctv_news WHERE date=? ORDER BY idx",
                    (date_str,))
    return [{"idx": r["idx"], "title": r["title"], "url": r["url"], "content": r["content"]}
            for r in rows]
