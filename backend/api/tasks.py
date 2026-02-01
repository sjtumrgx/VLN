"""Task management API endpoints"""

from typing import List

from fastapi import APIRouter, HTTPException

from backend.models.task import Task, TaskCreate, TaskStatus, TaskUpdate
from backend.storage.sqlite_client import SQLiteClient
from backend.config import settings

router = APIRouter(tags=["tasks"])

# 延迟初始化，在main.py中注入
_db: SQLiteClient = None


def set_db(db: SQLiteClient):
    """注入数据库实例"""
    global _db
    _db = db


def _get_db() -> SQLiteClient:
    if _db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return _db


@router.post("/create", response_model=Task)
async def create_task(req: TaskCreate):
    """创建新导航任务"""
    db = _get_db()
    task = Task(instruction=req.instruction, status=TaskStatus.PENDING)
    await db.create_task(task)
    return task


@router.get("/list", response_model=List[Task])
async def list_tasks(limit: int = 50):
    """获取任务列表"""
    db = _get_db()
    return await db.get_all_tasks(limit=limit)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """获取任务详情"""
    db = _get_db()
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=dict)
async def update_task(task_id: str, req: TaskUpdate):
    """更新任务"""
    db = _get_db()

    # 检查任务是否存在
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = req.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    await db.update_task(task_id, updates)
    return {"status": "updated", "task_id": task_id}


@router.get("/{task_id}/history")
async def get_task_history(task_id: str, limit: int = 50):
    """获取任务历史轨迹"""
    db = _get_db()

    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    trajectories = await db.get_task_history(task_id, limit=limit)
    return {"task_id": task_id, "trajectories": trajectories}
