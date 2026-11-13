# -*- coding: utf-8 -*-
"""定投（DCA）接口：历史定投回测。"""
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query

from ..sources import tencent

router = APIRouter(prefix="/api", tags=["dca"])

_PERIODS = ("day", "week", "month")


def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(400, "日期格式须为 YYYY-MM-DD")


def _xirr(cashflows):
    """cashflows: [(date, amount)]，amount 负=投入、正=回款。返回年化收益率（小数），无解返回 None。

    用「复利到期末」的等价式求内部收益率：sum(amt * (1+r)^((t_end - t_i)/365)) = 0。
    """
    end = cashflows[-1][0]

    def f(r):
        total = 0.0
        for d, amt in cashflows:
            total += amt * ((1.0 + r) ** ((end - d).days / 365.0))
        return total

    r = 0.1
    for _ in range(100):
        h = 1e-6
        df = (f(r + h) - f(r - h)) / (2 * h)
        if df == 0:
            return None
        r2 = r - f(r) / df
        if abs(r2 - r) < 1e-8:
            r = r2
            break
        r = r2
    else:
        return None
    return r if r > -0.99 else None


@router.get("/dca/backtest")
def dca_backtest(code: str = Query(...), start: str = Query(...), end: str = Query(...),
                 amount: float = Query(..., gt=0), period: str = Query("month")):
    """历史定投回测：区间内按周期定额买入（收盘价、前复权、允许零股），返回收益曲线与汇总。"""
    if period not in _PERIODS:
        raise HTTPException(400, "period 须为 %s" % "/".join(_PERIODS))
    start_d = _parse_date(start)
    end_d = _parse_date(end)
    if start_d >= end_d:
        raise HTTPException(400, "开始日期须早于结束日期")

    try:
        bars = tencent.kline(code, period="day", count=2000, fq="qfq")
    except ValueError as e:
        raise HTTPException(400, str(e))

    bars = [b for b in bars
            if start_d <= datetime.strptime(b["date"], "%Y-%m-%d").date() <= end_d]
    if not bars:
        raise HTTPException(400, "该区间内无行情数据（可能非交易日/停牌或代码有误）")
    bars.sort(key=lambda b: b["date"])

    # 定投日：day=每个交易日；week=每周首个交易日；month=每月首个交易日
    def _key(d):
        if period == "month":
            return (d.year, d.month)
        if period == "week":
            iso = d.isocalendar()
            return (iso[0], iso[1])
        return None

    invest_dates = []
    seen = set()
    for b in bars:
        d = datetime.strptime(b["date"], "%Y-%m-%d").date()
        k = _key(d)
        if period == "day":
            invest_dates.append(d)
        elif k not in seen:
            invest_dates.append(d)
            seen.add(k)

    invest_set = set(invest_dates)
    shares = 0.0
    cost = 0.0
    curve = []
    invests = []
    for b in bars:
        d = datetime.strptime(b["date"], "%Y-%m-%d").date()
        if d in invest_set:
            buy = amount / b["close"]
            shares += buy
            cost += amount
            invests.append({"date": b["date"], "price": b["close"], "amount": amount, "shares": buy})
        curve.append({"date": b["date"], "cost": round(cost, 2),
                      "value": round(shares * b["close"], 2), "price": b["close"]})

    final_value = shares * bars[-1]["close"]
    profit = final_value - cost
    return_pct = (profit / cost * 100) if cost else 0.0

    name = code
    try:
        q = tencent.tencent_quote([code])
        if code in q:
            name = q[code]["name"]
    except Exception:
        pass

    last_date = datetime.strptime(bars[-1]["date"], "%Y-%m-%d").date()
    cashflows = [(d, -amount) for d in invest_dates] + [(last_date, final_value)]
    annualized = _xirr(cashflows)

    return {
        "code": code, "name": name, "start": start, "end": end,
        "period": period, "amount": amount,
        "summary": {
            "invest_count": len(invests),
            "total_invested": round(cost, 2),
            "final_value": round(final_value, 2),
            "profit": round(profit, 2),
            "return_pct": round(return_pct, 2),
            "annualized_pct": round(annualized * 100, 2) if annualized is not None else None,
        },
        "curve": curve,
        "invests": invests,
    }
