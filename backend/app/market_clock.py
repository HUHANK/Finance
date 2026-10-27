# -*- coding: utf-8 -*-
"""交易日/交易时段判断。

不引节假日表：以腾讯日K里「今天有没有 bar」为准（自动覆盖节假日）。
- is_trading_day(d)：当日K线已产生 → 交易日（盘中 9:30 后才可判定）
- is_market_open()：本地时段粗判，配合 is_trading_day 决定是否轮询
"""
import datetime
import logging
import time

from . import db
from .sources import tencent

log = logging.getLogger(__name__)

_MORNING = (datetime.time(9, 30), datetime.time(11, 30))
_AFTERNOON = (datetime.time(13, 0), datetime.time(15, 0))


def _today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def is_trading_day(date_str=None):
    """当天是否交易日。判定为 True 永久缓存；False 每 15 分钟重查（当日bar可能还没出）。"""
    date_str = date_str or _today()
    cached = db.kv_get("trading_day:" + date_str)
    if cached is True:
        return True
    if datetime.date.fromisoformat(date_str).weekday() >= 5:
        return False
    now = time.time()
    if cached is False and now - (db.kv_get("trading_day_try:" + date_str) or 0) < 900:
        return False
    try:
        bars = tencent.kline("sh000001", period="day", count=10, fq="none")
        result = any(b["date"] == date_str for b in bars)
    except Exception as e:
        log.warning("trading-day kline check failed, fallback weekday: %s", e)
        return datetime.date.fromisoformat(date_str).weekday() < 5
    db.kv_set("trading_day:" + date_str, result)
    if not result:
        db.kv_set("trading_day_try:" + date_str, now)
    return result


def is_market_open(dt=None):
    """本地粗判是否开盘时段（不含节假日）。"""
    dt = dt or datetime.datetime.now()
    if dt.weekday() >= 5:
        return False
    t = dt.time()
    return _MORNING[0] <= t <= _MORNING[1] or _AFTERNOON[0] <= t <= _AFTERNOON[1]


def should_poll():
    """盯盘轮询总开关：时段在盘中，且今天是交易日。"""
    if not is_market_open():
        return False
    try:
        return is_trading_day()
    except Exception:
        return False


def latest_trade_date(max_back=15):
    """最近一个已产生K线的交易日（本地今天往前找）。"""
    bars = tencent.kline("sh000001", period="day", count=max_back, fq="none")
    return bars[-1]["date"] if bars else _today()
