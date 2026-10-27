# -*- coding: utf-8 -*-
"""美股数据源：腾讯财经 us 前缀行情（qt.gtimg.cn，字段以 ~ 分隔，布局与 A 股同族）。
实测：usDJI/usIXIC/usINX 指数、usXLK 等 ETF、usAAPL 等个股均可用。
时间字段为美东时间；成交额单位为美元；总市值单位为亿美元。

K线：指数(DJI/IXIC/INX) 走腾讯 newfqkline（原生含当日实时bar）；
个股/ETF 腾讯不给出历史，走新浪 US_MinKService 日线全量 + 本地重采样周/月。
"""
import json
import re

import requests

SESSION = requests.Session()
SESSION.trust_env = False  # 铁律：绕过系统代理（Clash）
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# 腾讯 newfqkline 原生支持的指数代码
US_TENCENT_INDEX = {"DJI", "IXIC", "INX"}


def us_quote(codes):
    """批量美股行情。codes 传 ['DJI','AAPL'] 或 'usDJI' 均可。
    返回按「原始输入代码」为键的 dict（不含 us 前缀），取不到的不在结果里。
    """
    codes = [str(c).strip() for c in codes if str(c).strip()]
    norm = {}
    for c in codes:
        key = c.lower()
        sym = c if key.startswith("us") else "us" + c
        norm[sym] = c
    out = {}
    items = list(norm.items())
    for i in range(0, len(items), 50):
        chunk = items[i:i + 50]
        url = "https://qt.gtimg.cn/q=" + ",".join(sym for sym, _ in chunk)
        try:
            r = SESSION.get(url, headers={"User-Agent": UA,
                                          "Referer": "https://gu.qq.com/"}, timeout=10)
            data = r.content.decode("gbk", "replace")
        except Exception:
            continue
        for line in data.strip().split(";"):
            line = line.strip()
            if "=" not in line or '"' not in line:
                continue
            sym = line.split("=")[0][2:]  # v_usAAPL -> usAAPL
            vals = line.split('"')[1].split("~")
            if len(vals) < 47:
                continue

            def f(idx):
                try:
                    return float(vals[idx]) if vals[idx] else None
                except (ValueError, TypeError):
                    return None

            out[norm.get(sym, sym)] = {
                "code": norm.get(sym, sym),
                "symbol": vals[2],           # 交易所后缀代码，如 AAPL.OQ
                "name": vals[1],             # 中文名
                "name_en": vals[46] if len(vals) > 46 else "",
                "price": f(3) or 0,
                "last_close": f(4) or 0,
                "open": f(5),
                "pct": f(32),
                "chg": f(31),
                "high": f(33),
                "low": f(34),
                "volume": f(36),             # 股
                "amount_usd": f(37),         # 美元
                "pe_ttm": f(39) if (f(39) or 0) > 0 else None,
                "mcap_total_yi": f(45),      # 亿美元
                "time": vals[30],            # 美东时间
            }
    return out


def _tencent_index_kline(code, period, count):
    """腾讯 newfqkline：美股三大指数日/周/月K（原生含当日实时bar）。"""
    sym = "us" + str(code).upper()
    url = "https://web.ifzq.gtimg.cn/appstock/app/newfqkline/get"
    r = SESSION.get(url, params={"param": "%s,%s,,,%d," % (sym, period, int(count))},
                    headers={"User-Agent": UA, "Referer": "https://gu.qq.com/"}, timeout=15)
    node = (r.json().get("data") or {}).get(sym) or {}
    rows = node.get(period) or []
    out = []
    for row in rows:
        try:
            out.append({"date": row[0], "open": float(row[1]), "close": float(row[2]),
                        "high": float(row[3]), "low": float(row[4]), "volume": float(row[5] or 0)})
        except (ValueError, IndexError, TypeError):
            continue
    return out[-int(count):]


def _sina_us_daily(code):
    """新浪美股日线全量历史（个股/ETF/指数均可用，指数带 . 前缀）。"""
    sym = str(code).lower()
    if sym in ("dji", "ixic", "inx"):
        sym = "." + sym
    url = ("https://stock.finance.sina.com.cn/usstock/api/jsonp_v2.php/"
           "var%%20t=/US_MinKService.getDailyK?symbol=%s" % sym)
    r = SESSION.get(url, headers={"User-Agent": UA,
                                  "Referer": "https://finance.sina.com.cn/"}, timeout=20)
    m = re.search(r"\((\[.*\])\)", r.content.decode("utf-8", "replace"), re.S)
    if not m:
        raise RuntimeError("新浪美股日线无数据: %s" % code)
    rows = json.loads(m.group(1))
    out = []
    for rec in rows:
        try:
            out.append({"date": rec["d"], "open": float(rec["o"]), "high": float(rec["h"]),
                        "low": float(rec["l"]), "close": float(rec["c"]),
                        "volume": float(rec.get("v") or 0)})
        except (KeyError, ValueError, TypeError):
            continue
    if not out:
        raise RuntimeError("新浪美股日线为空: %s" % code)
    return out


def _resample_ohlc(daily, period):
    """日线 → 周/月 OHLC（日期取组内最后一个交易日）。"""
    import pandas as pd
    df = pd.DataFrame(daily)
    df["dt"] = pd.to_datetime(df["date"])
    df = df.set_index("dt").sort_index()
    key = df.index.to_period("W") if period == "week" else df.index.to_period("M")
    out = []
    for _, g in df.groupby(key):
        out.append({"date": g.index[-1].strftime("%Y-%m-%d"),
                    "open": float(g["open"].iloc[0]), "high": float(g["high"].max()),
                    "low": float(g["low"].min()), "close": float(g["close"].iloc[-1]),
                    "volume": float(g["volume"].sum())})
    return out


def us_timeline(code):
    """美股当日分时（新浪 getMinK type=1，取数据中最近一个交易日的分钟线）。
    盘中含当日；收盘后/非交易日返回最近交易日的完整分时。
    返回 {date, points:[{time:'HHMM', price, cum_vol}]}，time 为美东时间。"""
    sym = str(code).lower()
    if sym in ("dji", "ixic", "inx"):
        sym = "." + sym
    url = ("https://stock.finance.sina.com.cn/usstock/api/jsonp_v2.php/"
           "var%%20t=/US_MinKService.getMinK?symbol=%s&type=1" % sym)
    r = SESSION.get(url, headers={"User-Agent": UA,
                                  "Referer": "https://finance.sina.com.cn/"}, timeout=20)
    m = re.search(r"\((\[.*\])\)", r.content.decode("utf-8", "replace"), re.S)
    if not m:
        raise RuntimeError("新浪美股分时无数据: %s" % code)
    rows = json.loads(m.group(1))
    if not rows:
        raise RuntimeError("新浪美股分时为空: %s" % code)
    day = max(str(rec.get("d", ""))[:10] for rec in rows)
    points, cum = [], 0.0
    for rec in rows:
        d = str(rec.get("d", ""))
        if d[:10] != day:
            continue
        try:
            cum += float(rec.get("v") or 0)
            points.append({"time": d[11:13] + d[14:16],
                           "price": float(rec["c"]), "cum_vol": cum})
        except (KeyError, ValueError, TypeError):
            continue
    return {"date": day, "points": points}


def us_kline(code, period="day", count=250, live_quote=None):
    """美股K线。
    - 指数(DJI/IXIC/INX)：腾讯 newfqkline，day/week/month 原生，含当日实时bar
    - 其他(个股/ETF)：新浪日线全量 → 周/月重采样；live_quote 传入时补当日未收盘bar
    返回按日期升序、最多 count 根的 [{date,open,close,high,low,volume}]。
    """
    c = str(code).upper()
    if c in US_TENCENT_INDEX:
        return _tencent_index_kline(c, period, count)

    daily = _sina_us_daily(c)
    bars = daily if period == "day" else _resample_ohlc(daily, period)
    bars = bars[-int(count):]
    if live_quote and bars:
        today = str(live_quote.get("time", ""))[:10]
        if today > bars[-1]["date"]:
            q = live_quote
            bars.append({"date": today,
                         "open": q.get("open") or q.get("price") or 0,
                         "high": q.get("high") or q.get("price") or 0,
                         "low": q.get("low") or q.get("price") or 0,
                         "close": q.get("price") or 0,
                         "volume": q.get("volume") or 0})
    return bars
