# -*- coding: utf-8 -*-
"""FastAPI 入口。开发态配合 vite(:5173) 用；前端 build 后直接托管 dist。"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, jobs
from .api import kline, news, profile, quotes, review, us, valuation, watchlist

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    jobs.start()
    yield
    jobs.shutdown()


app = FastAPI(title="Finance", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"], allow_headers=["*"],
)

app.include_router(quotes.router)
app.include_router(kline.router)
app.include_router(watchlist.router)
app.include_router(review.router)
app.include_router(valuation.router)
app.include_router(news.router)
app.include_router(profile.router)
app.include_router(us.router)

# 生产态：托管前端构建产物（SPA 回退到 index.html）
if os.path.isdir(config.FRONTEND_DIST):
    assets = os.path.join(config.FRONTEND_DIST, "assets")
    if os.path.isdir(assets):
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        target = os.path.join(config.FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(target):
            return FileResponse(target)
        return FileResponse(os.path.join(config.FRONTEND_DIST, "index.html"))
