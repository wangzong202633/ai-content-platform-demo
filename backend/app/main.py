# -*- coding: utf-8 -*-
"""企业AI营销内容智能管理平台 — Demo 后端入口.

Run:  python -m uvicorn app.main:app --port 8000
      (生产构建的前端从 backend/static 由本服务直接托管，单端口可整体对外)
"""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, seed
from .api import contents, media, misc, preferences

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    seed.seed()
    yield


app = FastAPI(title="企业AI营销内容智能管理平台 Demo", version="1.0.0-demo",
              description="黑客松 Demo 后端：内容生成 / 多渠道适配 / 审核闭环 / 老板偏好飞轮",
              lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(contents.router)
app.include_router(preferences.router)
app.include_router(misc.router)
app.include_router(media.router)

# 生产前端托管（vite build 产物放入 backend/static；API 路由已先注册，优先匹配）
if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))
