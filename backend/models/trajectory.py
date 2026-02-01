"""Trajectory data model"""

from datetime import datetime
from typing import List, Tuple

from pydantic import BaseModel, Field


class Waypoint(BaseModel):
    """单个航点"""
    x: float = Field(..., description="图像坐标X")
    y: float = Field(..., description="图像坐标Y")
    distance: float = Field(..., description="相对距离（用于颜色计算）")

    @property
    def color_rgb(self) -> Tuple[int, int, int]:
        """根据距离返回RGB颜色（绿色=近，红色=远）"""
        # 需要外部传入max_dist来归一化
        return (0, 255, 0)


class Trajectory(BaseModel):
    """轨迹模型，包含航点和速度指令"""
    waypoints: List[Waypoint] = Field(..., description="10-15个航点", min_length=1)
    v: float = Field(..., description="线速度 (m/s)")
    w: float = Field(..., description="角速度 (rad/s)")
    confidence: float = Field(default=0.0, description="置信度 [0, 1]")
    timestamp: datetime = Field(default_factory=datetime.now)

    @property
    def first_waypoint(self) -> Waypoint:
        """返回第一个航点（当前执行目标）"""
        return self.waypoints[0]

    @property
    def max_distance(self) -> float:
        """返回最远航点距离"""
        return max(wp.distance for wp in self.waypoints) if self.waypoints else 0.0
