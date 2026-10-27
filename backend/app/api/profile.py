# -*- coding: utf-8 -*-
"""个股/ETF/指数详情页聚合接口"""
from fastapi import APIRouter, HTTPException

from .. import pipelines
from ..sources import tencent, ths

router = APIRouter(prefix="/api/profile", tags=["profile"])

# 沪市指数白名单里的 6 位码 & 深市 399 开头 → 指数
_INDEX_6 = tencent.SH_INDEX | {"000001"}


def _kind(symbol, code6):
    mkt, num = symbol[:2], symbol[2:]
    if mkt == "sh" and num in _INDEX_6 and not num.startswith("5"):
        return "index"
    if mkt == "sz" and num.startswith("39"):
        return "index"
    if mkt == "sh" and num.startswith(("5", "56", "58")):
        return "etf"
    if mkt == "sz" and num.startswith(("15", "16")):
        return "etf"
    return "stock"


@router.get("")
def profile(code: str):
    try:
        symbol = tencent.with_market(code)
    except ValueError as e:
        raise HTTPException(400, str(e))
    quotes = tencent.tencent_quote([code])
    quote = quotes.get(code)
    code6 = tencent.norm_ticker(code)
    kind = _kind(symbol, code6)

    out = {"code": code, "symbol": symbol, "code6": code6, "kind": kind, "quote": quote}

    if kind == "stock":
        try:
            out["eps_forecast"] = ths.eps_forecast(code6)
        except Exception:
            out["eps_forecast"] = None

    if kind == "index":
        try:
            pipelines.ensure_valuation_history(code6)
            out["valuation"] = pipelines.valuation_summary(code6)
        except Exception:
            out["valuation"] = None
    return out
