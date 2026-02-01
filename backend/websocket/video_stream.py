"""WebSocket video stream handler"""

import json
import logging
from datetime import datetime
from typing import Dict

from fastapi import WebSocket, WebSocketDisconnect

from backend.models.task import TaskStatus
from backend.websocket.inference_pipeline import InferencePipeline

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.task_connections: Dict[str, str] = {}  # task_id -> client_id

    async def connect(self, client_id: str, websocket: WebSocket):
        """连接客户端"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"客户端 {client_id} 已连接")

    def disconnect(self, client_id: str):
        """断开客户端"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        # 清理任务绑定
        tasks_to_remove = [
            task_id for task_id, cid in self.task_connections.items() if cid == client_id
        ]
        for task_id in tasks_to_remove:
            del self.task_connections[task_id]
        logger.info(f"客户端 {client_id} 已断开")

    def bind_task(self, client_id: str, task_id: str):
        """绑定任务到客户端"""
        self.task_connections[task_id] = client_id

    async def send_to_client(self, client_id: str, message: dict):
        """发送消息到指定客户端"""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")

    async def send_to_task(self, task_id: str, message: dict):
        """发送消息到指定任务的客户端"""
        client_id = self.task_connections.get(task_id)
        if client_id:
            await self.send_to_client(client_id, message)


# 全局连接管理器
manager = ConnectionManager()


def _get_db():
    from backend.main import db

    return db


# 推理流水线：latest-frame-only
pipeline = InferencePipeline(send_to_client=manager.send_to_client, get_db=_get_db)


async def handle_video_stream(websocket: WebSocket, client_id: str):
    """处理视频流WebSocket连接"""
    await manager.connect(client_id, websocket)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)

            msg_type = message.get("type")

            if msg_type == "video_frame":
                task_id = message.get("task_id")
                frame_b64 = message.get("frame")
                frame_seq = int(message.get("frame_seq", 0))
                timestamp_ms = int(message.get("timestamp", 0))
                instruction = message.get("instruction", "向前移动")

                if not task_id or not frame_b64:
                    continue

                await pipeline.submit_frame(
                    task_id=task_id,
                    client_id=client_id,
                    frame_b64=frame_b64,
                    frame_seq=frame_seq,
                    timestamp_ms=timestamp_ms,
                    instruction=instruction,
                )

            elif msg_type == "bind_task":
                # 绑定任务
                task_id = message.get("task_id")
                if task_id:
                    manager.bind_task(client_id, task_id)
                    # 绑定即视为任务开始运行：写库更新状态（DB为真源）
                    try:
                        from backend.main import db

                        if db:
                            await db.update_task(task_id, {"status": TaskStatus.RUNNING})
                    except Exception as e:
                        logger.warning(f"bind_task 更新任务状态失败: {e}")
                    await pipeline.bind_task(task_id=task_id, client_id=client_id)
                    await manager.send_to_client(
                        client_id,
                        {
                            "type": "task_bound",
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

            elif msg_type == "stop_task":
                task_id = message.get("task_id")
                if task_id:
                    try:
                        from backend.main import db

                        if db:
                            await db.update_task(task_id, {"status": TaskStatus.STOPPED})
                    except Exception as e:
                        logger.warning(f"stop_task 更新任务状态失败: {e}")

                    await pipeline.stop_task(task_id)
                    await manager.send_to_client(
                        client_id,
                        {
                            "type": "task_stopped",
                            "task_id": task_id,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

            elif msg_type == "ping":
                # 心跳响应
                await manager.send_to_client(
                    client_id,
                    {"type": "pong", "timestamp": datetime.now().isoformat()},
                )

    except WebSocketDisconnect:
        await pipeline.disconnect_client(client_id)
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        await pipeline.disconnect_client(client_id)
        manager.disconnect(client_id)
