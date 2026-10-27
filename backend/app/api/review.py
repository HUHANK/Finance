# -*- coding: utf-8 -*-
"""复盘看板接口"""
import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db, market_clock, pipelines
from ..sources import tencent

router = APIRouter(prefix="/api/review", tags=["review"])


class RefreshBody(BaseModel):
    date: str = None


@router.get("")
def review(date: str = None):
    """某日快照。date 缺省取库里最新；无快照返回 empty，由前端引导刷新。"""
    dates = pipelines.snapshot_dates()
    target = date or (dates[0] if dates else market_clock.latest_trade_date())
    snap = pipelines.get_snapshot(target)
    return {"date": target, "snapshot": snap, "dates": dates}


@router.post("/refresh")
def refresh(body: RefreshBody):
    """手动（重）建快照。仅限近 10 根 bar 内的交易日。盘中数据不完整，自行斟酌。"""
    date = body.date or datetime.date.today().strftime("%Y-%m-%d")
    bars = tencent.kline("sh000001", period="day", count=10, fq="none")
    if not any(b["date"] == date for b in bars):
        raise HTTPException(400, "%s 不是最近 10 个交易日内的交易日" % date)
    try:
        snap = pipelines.build_review_snapshot(date)
    except Exception as e:
        raise HTTPException(502, "抓取失败: %s" % e)
    return {"date": date, "snapshot": snap, "dates": pipelines.snapshot_dates()}


@router.get("/etf-share-trend")
def etf_share_trend(code: str):
    """单只 ETF 的份额日序列（画趋势用）。"""
    rows = db.query("SELECT date, shares FROM etf_share WHERE code=? ORDER BY date", (code,))
    return {"code": code, "points": [{"date": r["date"], "shares": r["shares"]} for r in rows]}
