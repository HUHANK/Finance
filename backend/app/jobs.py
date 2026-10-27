# -*- coding: utf-8 -*-
"""盘后定时任务 + 启动补漏。"""
import datetime
import logging
import threading

from apscheduler.schedulers.background import BackgroundScheduler

from . import market_clock, pipelines

log = logging.getLogger(__name__)
_scheduler = None


def market_snapshot_job():
    """交易日 16:35：抓当日复盘快照。"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        if not market_clock.is_trading_day(today):
            return
        if pipelines.get_snapshot(today) is None:
            pipelines.build_review_snapshot(today)
            log.info("daily snapshot done: %s", today)
    except Exception as e:
        log.warning("snapshot job failed: %s", e)
    # 预留：到价/条件提醒的事件钩子放这里（v2）


def cctv_job():
    """周一至周五 21:05：抓当日新闻联播。"""
    today = datetime.date.today().strftime("%Y-%m-%d")
    try:
        if pipelines.ensure_cctv(today, with_content=True):
            log.info("cctv news stored: %s", today)
    except Exception as e:
        log.warning("cctv job failed: %s", e)


def backfill():
    """启动补漏（后台线程，不阻塞服务起监听）：
    - 最新交易日快照缺失则补（今天盘中未到 16:00 除外）
    - 今天 20:30 后联播缺失则补
    """
    try:
        latest = market_clock.latest_trade_date()
        today = datetime.date.today().strftime("%Y-%m-%d")
        after_close = datetime.datetime.now().time() >= datetime.time(16, 0)
        if pipelines.get_snapshot(latest) is None and (latest != today or after_close):
            pipelines.build_review_snapshot(latest)
            log.info("backfill snapshot: %s", latest)
    except Exception as e:
        log.warning("backfill snapshot failed: %s", e)
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        if datetime.datetime.now().time() >= datetime.time(20, 30):
            pipelines.ensure_cctv(today, with_content=True)
    except Exception as e:
        log.warning("backfill cctv failed: %s", e)


def start():
    global _scheduler
    threading.Thread(target=backfill, daemon=True, name="backfill").start()
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    _scheduler.add_job(market_snapshot_job, "cron", day_of_week="mon-fri",
                       hour=16, minute=35, id="snapshot")
    _scheduler.add_job(cctv_job, "cron", day_of_week="mon-fri",
                       hour=21, minute=5, id="cctv")
    _scheduler.start()
    log.info("scheduler started")


def shutdown():
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception:
            pass
