# -*- coding: utf-8 -*-
"""美股接口：指数 + 热门板块 + 热门个股 + K线，一次拉全。"""
from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..sources import us
from ..sources.us import us_kline, us_quote, us_timeline

router = APIRouter(prefix="/api/us", tags=["us"])

_PERIODS = ("day", "week", "month")


def _pack(quotes, order):
    return [quotes[c] for c in order if c in quotes]


@router.get("/overview")
def overview():
    idx_quotes = us_quote([c for c, _ in config.US_INDICES])
    sec_quotes = us_quote([c for c, _ in config.US_SECTORS])
    giants = us_quote(config.US_GIANTS)
    china = us_quote(config.US_CHINA)

    indices = []
    for code, label in config.US_INDICES:
        q = idx_quotes.get(code)
        if q:
            # 三大指数没有可用的免费分时源（新浪指数分钟库是旧样本），只提供 K 线
            indices.append({**q, "label": label,
                            "has_timeline": code.upper() not in us.US_TENCENT_INDEX})

    sectors = []
    for code, label in config.US_SECTORS:
        q = sec_quotes.get(code)
        if q:
            sectors.append({**q, "label": label})
    sectors.sort(key=lambda s: s["pct"] if s["pct"] is not None else -999, reverse=True)

    return {
        "indices": indices,
        "sectors": sectors,
        "giants": _pack(giants, config.US_GIANTS),
        "china": _pack(china, config.US_CHINA),
        "time": (indices[0]["time"] if indices else ""),
    }


@router.get("/kline")
def kline(code: str = Query(...), period: str = Query("day"),
          count: int = Query(250, ge=10, le=2000)):
    """美股/美股指数的日/周/月K线。个股/ETF 会拼当日实时bar。"""
    if period not in _PERIODS:
        raise HTTPException(400, "period 须为 %s" % "/".join(_PERIODS))
    try:
        live = us_quote([code]).get(str(code).upper())
        bars = us_kline(code, period=period, count=count, live_quote=live)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    return {"code": code, "period": period, "bars": bars}


@router.get("/timeline")
def timeline(code: str = Query(...)):
    """美股当日分时（最近一个交易日；last_close 取自实时行情）。
    三大指数（DJI/IXIC/INX）暂无可用分时源，返回 400。"""
    if str(code).upper() in us.US_TENCENT_INDEX:
        raise HTTPException(400, "该指数暂无分时数据源，请看日K")
    try:
        live = us_quote([code]).get(str(code).upper())
        tl = us_timeline(code)
    except RuntimeError as e:
        raise HTTPException(502, str(e))
    tl["last_close"] = live.get("last_close") if live else None
    return tl
