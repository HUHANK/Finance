# -*- coding: utf-8 -*-
"""SQLite 访问层：连接管理、建表、通用 kv 缓存"""
import json
import os
import sqlite3
import threading

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS watchlist(
    code     TEXT PRIMARY KEY,          -- 保留用户写法：股票/ETF 用 6 位，指数带前缀如 sh000001
    name     TEXT DEFAULT '',
    sort     INTEGER DEFAULT 0,
    added_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS daily_snapshot(
    date       TEXT PRIMARY KEY,        -- 交易日 YYYY-MM-DD
    payload    TEXT NOT NULL,           -- 复盘看板 JSON
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS etf_share(
    date   TEXT,
    code   TEXT,
    name   TEXT,
    shares REAL,                        -- 万份
    PRIMARY KEY(date, code)
);
CREATE TABLE IF NOT EXISTS cctv_news(
    date    TEXT,
    idx     INTEGER,
    title   TEXT,
    url     TEXT,
    content TEXT,
    PRIMARY KEY(date, idx)
);
CREATE TABLE IF NOT EXISTS valuation_history(
    index_code TEXT,
    date       TEXT,
    pe_total   REAL,
    pe_calc    REAL,
    dy_total   REAL,
    dy_calc    REAL,
    PRIMARY KEY(index_code, date)
);
CREATE TABLE IF NOT EXISTS pe_history(
    index_code TEXT,
    date       TEXT,                    -- 官网日频 PE 长序列（口径以官网为准，内部一致可算分位）
    pe         REAL,
    PRIMARY KEY(index_code, date)
);
CREATE TABLE IF NOT EXISTS index_weights(
    index_code TEXT,
    date       TEXT,
    code       TEXT,
    name       TEXT,
    weight     REAL,
    PRIMARY KEY(index_code, date, code)
);
CREATE TABLE IF NOT EXISTS kv_cache(
    key        TEXT PRIMARY KEY,
    value      TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

# 首次启动的默认自选（统一带市场前缀的规范写法，避免 000001 之类的歧义码）
DEFAULT_WATCHLIST = [
    "sh000001", "sz399006", "sh000688",
    "sh510300", "sz159994", "sh518880", "sh512100",
]


def get_conn():
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _local.conn = conn
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM watchlist").fetchone()[0] == 0:
        for i, code in enumerate(DEFAULT_WATCHLIST):
            conn.execute(
                "INSERT OR IGNORE INTO watchlist(code, sort) VALUES(?,?)", (code, i))
    conn.commit()


def query(sql, params=()):
    rows = get_conn().execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def execute(sql, params=()):
    conn = get_conn()
    cur = conn.execute(sql, params)
    conn.commit()
    return cur.rowcount


def executemany(sql, seq):
    conn = get_conn()
    conn.executemany(sql, seq)
    conn.commit()


def kv_get(key, default=None):
    rows = query("SELECT value FROM kv_cache WHERE key=?", (key,))
    if not rows:
        return default
    try:
        return json.loads(rows[0]["value"])
    except (ValueError, TypeError):
        return default


def kv_set(key, value):
    execute(
        "INSERT INTO kv_cache(key, value, updated_at) VALUES(?,?,datetime('now','localtime')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
        (key, json.dumps(value, ensure_ascii=False)))
