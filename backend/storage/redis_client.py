"""Redis client for caching and message queue"""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from backend.models.trajectory import Trajectory

logger = logging.getLogger(__name__)


class RedisClient:
    """异步Redis客户端"""

    def __init__(self, redis_url: str, db: int = 0):
        self.redis_url = redis_url
        self.db = db
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self):
        """连接到Redis"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url, db=self.db, decode_responses=True
            )
            # 测试连接
            await self.redis.ping()
            self._connected = True
            logger.info("✓ Redis连接成功")
        except Exception as e:
            logger.warning(f"⚠ Redis连接失败: {e}，将使用降级模式")
            self._connected = False

    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
            self._connected = False

    async def set_current_task(self, task_id: str, data: dict, ttl: int = 3600):
        """设置当前任务（1小时TTL）"""
        if not self._connected:
            return False

        try:
            await self.redis.setex(
                f"task:current:{task_id}", ttl, json.dumps(data)
            )
            return True
        except Exception as e:
            logger.error(f"Redis set_current_task错误: {e}")
            return False

    async def get_current_task(self, task_id: str) -> Optional[dict]:
        """获取当前任务"""
        if not self._connected:
            return None

        try:
            data = await self.redis.get(f"task:current:{task_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get_current_task错误: {e}")
            return None

    async def push_video_frame(self, frame_data: bytes):
        """推送视频帧到队列（FIFO）"""
        if not self._connected:
            return False

        try:
            await self.redis.lpush("video_frames", frame_data)
            # 限制队列长度，防止内存溢出
            await self.redis.ltrim("video_frames", 0, 9)
            return True
        except Exception as e:
            logger.error(f"Redis push_video_frame错误: {e}")
            return False

    async def pop_video_frame(self) -> Optional[bytes]:
        """获取视频帧（FIFO）"""
        if not self._connected:
            return None

        try:
            frame = await self.redis.rpop("video_frames")
            return frame.encode() if frame else None
        except Exception as e:
            logger.error(f"Redis pop_video_frame错误: {e}")
            return None

    async def cache_trajectory(
        self, task_id: str, trajectory: Trajectory, ttl: int = 300
    ):
        """缓存最新轨迹（5分钟TTL）"""
        if not self._connected:
            return False

        try:
            await self.redis.setex(
                f"trajectory:latest:{task_id}",
                ttl,
                trajectory.model_dump_json(),
            )
            return True
        except Exception as e:
            logger.error(f"Redis cache_trajectory错误: {e}")
            return False

    async def get_cached_trajectory(self, task_id: str) -> Optional[Trajectory]:
        """获取缓存的轨迹"""
        if not self._connected:
            return None

        try:
            data = await self.redis.get(f"trajectory:latest:{task_id}")
            if data:
                return Trajectory.model_validate_json(data)
        except Exception as e:
            logger.error(f"Redis get_cached_trajectory错误: {e}")
        return None

    @property
    def is_connected(self) -> bool:
        """检查Redis是否连接"""
        return self._connected
