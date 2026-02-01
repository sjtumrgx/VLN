"""Navigation command data model"""

from typing import Optional

from pydantic import BaseModel, Field

from .trajectory import Trajectory


class NavigationCommand(BaseModel):
    """导航指令输出"""
    task_id: str = Field(..., description="关联任务ID")
    trajectory: Trajectory = Field(..., description="规划轨迹")
    confidence: float = Field(default=0.0, description="置信度")
    reasoning: Optional[str] = Field(default=None, description="推理过程描述")
    reached_goal: bool = Field(default=False, description="是否已到达目标")


class VLLMResponse(BaseModel):
    """vLLM推理结果的结构化输出"""
    spatial_analysis: str = Field(default="", description="空间分析描述")
    action: str = Field(default="move_forward", description="推荐动作")
    goal_direction: dict = Field(
        default_factory=lambda: {"azimuth": 0.0, "distance": 5.0},
        description="目标方向（方位角和距离）",
    )
    obstacles: list = Field(default_factory=list, description="障碍物列表")
    confidence: float = Field(default=0.5, description="置信度")
    reached_goal: bool = Field(default=False, description="是否到达目标")
