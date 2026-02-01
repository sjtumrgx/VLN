"""Task data model"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskCreate(BaseModel):
    """创建任务的请求体"""
    instruction: str = Field(..., description="自然语言导航指令", min_length=1)


class TaskUpdate(BaseModel):
    """更新任务的请求体"""
    status: Optional[TaskStatus] = None
    instruction: Optional[str] = None
    memory_summary: Optional[str] = None


class Task(BaseModel):
    """任务模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    memory_summary: Optional[str] = None

    class Config:
        from_attributes = True
