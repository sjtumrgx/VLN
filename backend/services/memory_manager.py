"""Memory management for task context"""

import logging
from typing import List, Optional

from backend.config import settings
from backend.storage.sqlite_client import SQLiteClient

logger = logging.getLogger(__name__)


class MemoryManager:
    """任务记忆管理器 - 滑动窗口策略"""

    def __init__(self, db: SQLiteClient):
        self.db = db
        self.window_size = settings.MEMORY_WINDOW_SIZE
        self.summary_length = settings.MEMORY_SUMMARY_LENGTH

    async def get_task_memory(self, task_id: str) -> str:
        """
        获取任务记忆摘要

        Args:
            task_id: 任务ID

        Returns:
            记忆摘要文本
        """
        # 从数据库获取任务
        task = await self.db.get_task(task_id)
        if not task:
            return ""

        # 如果有现有摘要，直接返回
        if task.memory_summary:
            return task.memory_summary

        # 否则生成新摘要
        return await self._generate_summary(task_id)

    async def _generate_summary(self, task_id: str) -> str:
        """从历史轨迹生成摘要"""
        # 获取最近的轨迹记录
        history = await self.db.get_task_history(task_id, limit=self.summary_length)

        if not history:
            return "任务刚开始，无历史记录"

        # 简单摘要：记录最近的关键事件
        events = []
        for idx, traj in enumerate(history[::-1]):  # 倒序，从最早到最近
            v = traj["v"]
            w = traj["w"]

            if abs(w) > 0.3:  # 明显转向
                direction = "左转" if w > 0 else "右转"
                events.append(f"{idx+1}. {direction} (角速度{w:.2f})")
            elif v < 0.2:  # 速度很慢或停止
                events.append(f"{idx+1}. 减速/停止 (速度{v:.2f})")
            elif v > 0.6:  # 快速前进
                events.append(f"{idx+1}. 快速前进 (速度{v:.2f})")

        if not events:
            return "平稳前进中"

        return "最近动作: " + "; ".join(events[-3:])  # 保留最近3个事件

    async def update_memory(self, task_id: str, new_observation: str):
        """
        更新任务记忆

        Args:
            task_id: 任务ID
            new_observation: 新观察（如VLM的spatial_analysis）
        """
        # 重新生成摘要
        summary = await self._generate_summary(task_id)

        # 添加新观察
        if new_observation:
            summary = f"{summary}; 当前: {new_observation[:50]}"  # 限制长度

        # 更新到数据库
        await self.db.update_task(task_id, {"memory_summary": summary})

        logger.debug(f"任务 {task_id} 记忆已更新: {summary}")
