"""WebSocket video stream handler"""

import asyncio
import base64
import json
import logging
from datetime import datetime
from typing import Dict

import cv2
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from backend.config import settings

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
                # 处理视频帧
                await process_video_frame(message, client_id)

            elif msg_type == "bind_task":
                # 绑定任务
                task_id = message.get("task_id")
                if task_id:
                    manager.bind_task(client_id, task_id)
                    await manager.send_to_client(
                        client_id,
                        {
                            "type": "task_bound",
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
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(client_id)


async def process_video_frame(message: dict, client_id: str):
    """处理视频帧 - 完整pipeline"""
    from backend.services.vllm_client import VLLMClient
    from backend.services.path_planner import PathPlanner
    from backend.services.memory_manager import MemoryManager
    from backend.utils.visualization import draw_trajectory_on_frame
    from backend.main import db

    task_id = message.get("task_id")
    frame_b64 = message.get("frame")
    timestamp = message.get("timestamp", 0)
    instruction = message.get("instruction", "向前移动")

    if not frame_b64:
        return

    try:
        # 解码图像
        frame_bytes = base64.b64decode(frame_b64)
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            logger.warning("无效的图像帧")
            return

        # 初始化服务（延迟初始化，避免循环导入）
        vllm_client = VLLMClient()
        path_planner = PathPlanner()
        memory_manager = MemoryManager(db) if db else None

        # 获取任务记忆
        memory = ""
        if memory_manager and task_id:
            memory = await memory_manager.get_task_memory(task_id)

        # 1. vLLM推理
        vllm_result = await vllm_client.analyze_frame(frame, instruction, memory)

        if vllm_result is None:
            # vLLM推理失败，返回原始帧
            logger.warning("vLLM推理失败，返回原始帧")
            _, buffer = cv2.imencode(".jpg", frame)
            processed_frame_b64 = base64.b64encode(buffer).decode("utf-8")

            await manager.send_to_client(
                client_id,
                {
                    "type": "navigation_result",
                    "task_id": task_id,
                    "frame_with_trajectory": processed_frame_b64,
                    "v": 0.0,
                    "w": 0.0,
                    "waypoints": [],
                    "timestamp": datetime.now().timestamp() * 1000,
                    "latency": datetime.now().timestamp() * 1000 - timestamp,
                    "error": "vLLM inference failed",
                },
            )
            return

        # 2. 路径规划
        trajectory = path_planner.plan(vllm_result)

        # 3. 绘制轨迹
        frame_with_traj = draw_trajectory_on_frame(frame, trajectory)

        # 4. 编码图像
        _, buffer = cv2.imencode(".jpg", frame_with_traj, [cv2.IMWRITE_JPEG_QUALITY, 85])
        processed_frame_b64 = base64.b64encode(buffer).decode("utf-8")

        # 5. 保存轨迹到数据库
        if db and task_id:
            await db.save_trajectory(task_id, trajectory)

        # 6. 更新记忆
        if memory_manager and task_id:
            await memory_manager.update_memory(task_id, vllm_result.spatial_analysis)

        # 7. 发送结果
        await manager.send_to_client(
            client_id,
            {
                "type": "navigation_result",
                "task_id": task_id,
                "frame_with_trajectory": processed_frame_b64,
                "v": trajectory.v,
                "w": trajectory.w,
                "waypoints": [
                    {"x": wp.x, "y": wp.y, "distance": wp.distance}
                    for wp in trajectory.waypoints
                ],
                "confidence": trajectory.confidence,
                "reached_goal": vllm_result.reached_goal,
                "spatial_analysis": vllm_result.spatial_analysis,
                "timestamp": datetime.now().timestamp() * 1000,
                "latency": datetime.now().timestamp() * 1000 - timestamp,
            },
        )

        logger.info(
            f"处理完成: v={trajectory.v:.2f}, w={trajectory.w:.2f}, "
            f"conf={trajectory.confidence:.2f}"
        )

    except Exception as e:
        logger.error(f"处理视频帧错误: {e}", exc_info=True)
