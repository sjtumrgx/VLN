"""SQLite storage client for tasks and trajectories"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

from backend.models.task import Task, TaskStatus
from backend.models.trajectory import Trajectory


class SQLiteClient:
    """异步SQLite客户端"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 创建tasks表
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    instruction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    memory_summary TEXT
                )
                """
            )

            # 创建trajectories表
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS trajectories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    waypoints TEXT,
                    v REAL,
                    w REAL,
                    confidence REAL,
                    timestamp TIMESTAMP,
                    FOREIGN KEY(task_id) REFERENCES tasks(id)
                )
                """
            )

            # 创建索引
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_id ON trajectories(task_id)"
            )
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_timestamp ON trajectories(timestamp)"
            )

            await db.commit()

    async def create_task(self, task: Task) -> Task:
        """创建新任务"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO tasks (id, instruction, status, created_at, updated_at, memory_summary)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
                    task.instruction,
                    task.status.value,
                    task.created_at,
                    task.updated_at,
                    task.memory_summary,
                ),
            )
            await db.commit()
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """查询任务"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Task(
                        id=row["id"],
                        instruction=row["instruction"],
                        status=TaskStatus(row["status"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        memory_summary=row["memory_summary"],
                    )
        return None

    async def update_task(self, task_id: str, updates: dict) -> bool:
        """更新任务"""
        set_clauses = []
        values = []

        for key, value in updates.items():
            if key == "status" and isinstance(value, TaskStatus):
                value = value.value
            set_clauses.append(f"{key} = ?")
            values.append(value)

        # 总是更新updated_at
        set_clauses.append("updated_at = ?")
        values.append(datetime.now())

        values.append(task_id)

        query = f"UPDATE tasks SET {', '.join(set_clauses)} WHERE id = ?"

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, values)
            await db.commit()
            return True

    async def get_all_tasks(self, limit: int = 100) -> List[Task]:
        """获取所有任务"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    Task(
                        id=row["id"],
                        instruction=row["instruction"],
                        status=TaskStatus(row["status"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        memory_summary=row["memory_summary"],
                    )
                    for row in rows
                ]

    async def save_trajectory(
        self, task_id: str, trajectory: Trajectory
    ) -> int:
        """保存轨迹"""
        waypoints_json = json.dumps([wp.model_dump() for wp in trajectory.waypoints])

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO trajectories (task_id, waypoints, v, w, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    waypoints_json,
                    trajectory.v,
                    trajectory.w,
                    trajectory.confidence,
                    trajectory.timestamp,
                ),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_task_history(self, task_id: str, limit: int = 50) -> List[dict]:
        """获取任务历史轨迹"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM trajectories
                WHERE task_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (task_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "task_id": row["task_id"],
                        "waypoints": json.loads(row["waypoints"]),
                        "v": row["v"],
                        "w": row["w"],
                        "confidence": row["confidence"],
                        "timestamp": row["timestamp"],
                    }
                    for row in rows
                ]
