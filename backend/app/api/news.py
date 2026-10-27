# -*- coding: utf-8 -*-
"""新闻接口（v1: 新闻联播；财联社电报源留位）"""
import datetime

from fastapi import APIRouter

from .. import pipelines

router = APIRouter(prefix="/api/news", tags=["news"])

_CCTV_MAX_BACK = 4  # latest 往前找的最大天数


@router.get("/cctv/dates")
def cctv_dates():
    return {"dates": pipelines.cctv_dates()}


@router.get("/cctv/latest")
def cctv_latest():
    """从今天往前找最近一期已发布的联播（自动入库）。"""
    today = datetime.date.today()
    for i in range(_CCTV_MAX_BACK):
        date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        try:
            pipelines.ensure_cctv(date, with_content=True)
        except Exception:
            continue
        items = pipelines.cctv_items(date)
        if items:
            return {"date": date, "items": items}
    return {"date": None, "items": []}


@router.get("/cctv")
def cctv(date: str):
    """指定日期联播；库里没有就现抓（未发布返回空列表）。"""
    try:
        pipelines.ensure_cctv(date, with_content=True)
    except Exception:
        pass
    return {"date": date, "items": pipelines.cctv_items(date)}
