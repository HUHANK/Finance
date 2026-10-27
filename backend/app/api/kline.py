# -*- coding: utf-8 -*-
"""K线/分时接口"""
from fastapi import APIRouter, HTTPException, Query

from ..sources import tencent

router = APIRouter(prefix="/api", tags=["kline"])

_PERIODS = ("day", "week", "month")
_FQS = ("qfq", "hfq", "none")


@router.get("/kline")
def kline(code: str = Query(...), period: str = Query("day"), fq: str = Query("qfq"),
          count: int = Query(320, ge=10, le=2000)):
    if period not in _PERIODS:
        raise HTTPException(400, "period 须为 %s" % "/".join(_PERIODS))
    if fq not in _FQS:
        raise HTTPException(400, "fq 须为 %s" % "/".join(_FQS))
    try:
        bars = tencent.kline(code, period=period, count=count, fq=fq)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"code": code, "period": period, "fq": fq, "bars": bars}


@router.get("/timeline")
def timeline(code: str = Query(...)):
    """当日分时（非交易日返回最近交易日的）。"""
    try:
        return tencent.minute_line(code)
    except ValueError as e:
        raise HTTPException(400, str(e))
