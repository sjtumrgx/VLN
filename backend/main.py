"""
VLN System - FastAPI main entry point
Usage: uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload
"""

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api import health, tasks, models
from backend.config import settings
from backend.storage.sqlite_client import SQLiteClient
from backend.storage.redis_client import RedisClient
from backend.websocket.video_stream import handle_video_stream

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# 全局实例
db: SQLiteClient = None
redis: RedisClient = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global db, redis

    # === Startup ===
    logger.info("=== VLN System 启动 ===")

    # 初始化SQLite
    db = SQLiteClient(settings.SQLITE_DB_PATH)
    await db.init_db()
    logger.info(f"✓ SQLite数据库已初始化: {settings.SQLITE_DB_PATH}")

    # 注入数据库到tasks路由
    tasks.set_db(db)

    # 初始化Redis（允许失败，降级运行）
    redis = RedisClient(settings.REDIS_URL, settings.REDIS_DB)
    await redis.connect()

    logger.info(f"✓ 服务就绪: http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    logger.info(f"  vLLM地址: {settings.VLLM_API_URL}")
    logger.info(f"  默认模型: {settings.DEFAULT_MODEL}")

    yield

    # === Shutdown ===
    logger.info("=== VLN System 关闭 ===")
    if redis:
        await redis.close()


app = FastAPI(
    title="VLN System",
    description="Vision-Language Navigation System for Quadruped Robots",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/health")
app.include_router(tasks.router, prefix="/api/tasks")
app.include_router(models.router, prefix="/api/models")


# WebSocket 端点
@app.websocket("/ws/video")
async def video_ws(websocket: WebSocket, client_id: str = None):
    """视频流WebSocket端点"""
    if not client_id:
        client_id = str(uuid.uuid4())[:8]
    await handle_video_stream(websocket, client_id)


@app.websocket("/ws/control")
async def control_ws(websocket: WebSocket):
    """控制信号WebSocket端点"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # 处理控制信号
            await websocket.send_json({"status": "received", "data": data})
    except Exception:
        pass
