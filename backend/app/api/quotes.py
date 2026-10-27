# -*- coding: utf-8 -*-
"""实时行情接口"""
from fastapi import APIRouter, HTTPException, Query

from .. import config
from ..sources import tencent

router = APIRouter(prefix="/api", tags=["quotes"])


@router.get("/quotes")
def quotes(codes: str = Query(..., description="逗号分隔，如 sh000001,159994")):
    lst = [c.strip() for c in codes.split(",") if c.strip()]
    if not lst:
        raise HTTPException(400, "codes 为空")
    try:
        data = tencent.tencent_quote(lst)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"quotes": data}


@router.get("/indices")
def indices():
    """盯盘页顶部指数一览。"""
    codes = [c for c, _ in config.INDEX_OVERVIEW]
    quotes = tencent.tencent_quote(codes)
    return {"order": codes, "names": dict(config.INDEX_OVERVIEW), "quotes": quotes}
