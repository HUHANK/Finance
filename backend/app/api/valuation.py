# -*- coding: utf-8 -*-
"""指数估值接口"""
import time

from fastapi import APIRouter, HTTPException

from .. import config, db, pipelines
from ..sources import tencent, ths

router = APIRouter(prefix="/api/valuation", tags=["valuation"])


@router.get("/presets")
def presets():
    return {"items": [{"code": c, "name": n} for c, n in config.VALUATION_PRESETS]}


@router.get("")
def valuation(index: str):
    """估值页主数据：PE 长序列（2011 起，画曲线+百分位）+ 官方近期 PE1/PE2/股息率。"""
    try:
        pipelines.ensure_pe_history(index)
    except Exception as e:
        raise HTTPException(502, "拉取 PE 历史失败: %s" % e)
    pe_history = [{"date": r["date"], "pe": r["pe"]} for r in pipelines.pe_history_rows(index)]
    recent = [{"date": r["date"], "pe_total": r["pe_total"], "pe_calc": r["pe_calc"],
               "dy_total": r["dy_total"]}
              for r in db.query(
                  "SELECT date, pe_total, pe_calc, dy_total FROM valuation_history "
                  "WHERE index_code=? ORDER BY date", (index,))]
    return {"index": index, "pe_history": pe_history, "recent_official": recent,
            "summary": pipelines.valuation_summary(index)}


@router.get("/weights")
def weights(index: str, top: int = 20):
    """成份权重（官方月度文件）+ 现价行情。"""
    try:
        pipelines.ensure_index_weights(index)
    except Exception as e:
        raise HTTPException(502, "拉取权重失败: %s" % e)
    rows = db_weights(index, top)
    quotes = tencent.tencent_quote([r["code"] for r in rows]) if rows else {}
    for r in rows:
        q = quotes.get(r["code"]) or {}
        r["price"] = q.get("price")
        r["pct"] = q.get("pct")
        r["pe_ttm"] = q.get("pe_ttm")
    snap_date = rows[0]["date"] if rows else None
    return {"index": index, "snapshot_date": snap_date, "items": rows}


@router.post("/forecast")
def forecast(index: str, top: int = 15):
    """一致预期加权汇总（重接口：逐股抓同花顺，约 15 秒）。"""
    try:
        pipelines.ensure_index_weights(index)
    except Exception as e:
        raise HTTPException(502, "拉取权重失败: %s" % e)
    rows = db_weights(index, top)
    per_stock, ok = [], []
    for r in rows:
        fc = None
        try:
            fc = ths.eps_forecast(r["code"])
        except Exception:
            fc = None
        q = (tencent.tencent_quote([r["code"]]) or {}).get(r["code"]) or {}
        pe_ttm = q.get("pe_ttm")
        eps_ttm = (q.get("price") / pe_ttm) if (q.get("price") and pe_ttm) else None
        eps26 = eps27 = None
        if fc and len(fc) >= 1:
            eps26 = fc[0]["eps"]
            if len(fc) >= 2:
                eps27 = fc[1]["eps"]
        item = {"code": r["code"], "name": r["name"], "weight": r["weight"],
                "price": q.get("price"), "pe_ttm": pe_ttm, "eps_ttm": eps_ttm,
                "eps26": eps26, "eps27": eps27, "orgs": (fc[0]["orgs"] if fc else None)}
        per_stock.append(item)
        if eps26 and eps_ttm:
            ok.append(item)
        time.sleep(0.6)
    if not ok:
        return {"index": index, "summary": None, "items": per_stock}
    wsum = sum(x["weight"] for x in ok)
    e_ttm = sum(x["weight"] * x["eps_ttm"] for x in ok) / wsum
    e26 = sum(x["weight"] * x["eps26"] for x in ok) / wsum
    ok2 = [x for x in ok if x["eps27"]]
    wsum2 = sum(x["weight"] for x in ok2)
    e27 = sum(x["weight"] * x["eps27"] for x in ok2) / wsum2 if ok2 else None
    g_ttm26 = e26 / e_ttm - 1
    g_2627 = (e27 / e26 - 1) if (ok2 and e26) else None
    vs = pipelines.valuation_summary(index) or {}
    pe1 = vs.get("pe1_official") or vs.get("pe_last")
    summary = {
        "covered_weight": round(wsum2 or wsum, 1),
        "covered_n": len(ok),
        "pe_ttm_official": pe1,
        "basket_pe_ttm": round(wsum / sum(x["weight"] / x["pe_ttm"] for x in ok), 2)
        if all(x["pe_ttm"] for x in ok) else None,
        "g_ttm_to_26e": round(g_ttm26 * 100, 1) if g_ttm26 is not None else None,
        "g_26e_to_27e": round(g_2627 * 100, 1) if g_2627 is not None else None,
        "pe_26e": round(pe1 / (1 + g_ttm26), 2) if (pe1 and g_ttm26 is not None) else None,
        "pe_27e": round(pe1 / (1 + g_ttm26) / (1 + g_2627), 2)
        if (pe1 and g_ttm26 is not None and g_2627 is not None) else None,
        "peg": round(pe1 / (1 + g_ttm26) / (g_2627 * 100), 2)
        if (pe1 and g_ttm26 is not None and g_2627 not in (None, 0)) else None,
    }
    return {"index": index, "summary": summary, "items": per_stock}


def db_weights(index, top):
    return db.query(
        "SELECT date, code, name, weight FROM index_weights WHERE index_code=? "
        "ORDER BY weight DESC LIMIT ?", (index, int(top)))
