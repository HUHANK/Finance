# -*- coding: utf-8 -*-
"""自选股管理"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import db, market_clock
from ..sources import tencent

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


class AddBody(BaseModel):
    code: str


def _canonical(code: str) -> str:
    try:
        return tencent.with_market(code)
    except ValueError:
        raise HTTPException(400, "代码格式不对: %s（示例 600519 / sh000001 / 159994.SZ）" % code)


@router.get("")
def list_watchlist():
    rows = db.query("SELECT code, name FROM watchlist ORDER BY sort, added_at")
    quotes = tencent.tencent_quote([r["code"] for r in rows]) if rows else {}
    items = []
    for r in rows:
        q = quotes.get(r["code"])
        if q and not r["name"]:
            db.execute("UPDATE watchlist SET name=? WHERE code=?", (q["name"], r["code"]))
        items.append({"code": r["code"], "name": (q["name"] if q else r["name"]),
                      "quote": q})
    return {"items": items, "polling": market_clock.should_poll()}


@router.post("")
def add_watchlist(body: AddBody):
    code = _canonical(body.code)
    if db.query("SELECT 1 FROM watchlist WHERE code=?", (code,)):
        raise HTTPException(409, "已在自选中: %s" % code)
    name = ""
    try:
        q = tencent.tencent_quote([code])
        name = (q.get(code) or {}).get("name", "")
    except Exception:
        pass
    max_sort = db.query("SELECT COALESCE(MAX(sort),0) AS m FROM watchlist")[0]["m"]
    db.execute("INSERT INTO watchlist(code, name, sort) VALUES(?,?,?)", (code, name, max_sort + 1))
    return {"code": code, "name": name}


@router.delete("/{code}")
def remove_watchlist(code: str):
    n = db.execute("DELETE FROM watchlist WHERE code=?", (_canonical(code),))
    if not n:
        raise HTTPException(404, "不在自选中: %s" % code)
    return {"deleted": code}
