"""Path planning module using Bezier curves and DWA"""

import logging
from typing import Tuple

import numpy as np
from scipy.interpolate import make_interp_spline

from backend.config import settings
from backend.models.navigation import VLLMResponse
from backend.models.trajectory import Trajectory, Waypoint

logger = logging.getLogger(__name__)


class PathPlanner:
    """路径规划器 - 贝塞尔曲线 + 动态窗口法"""

    def __init__(self):
        self.num_waypoints = settings.NUM_WAYPOINTS
        self.max_v = settings.MAX_LINEAR_VELOCITY
        self.max_w = settings.MAX_ANGULAR_VELOCITY
        self.image_width = settings.VIDEO_STREAM_RESOLUTION_WIDTH
        self.image_height = settings.VIDEO_STREAM_RESOLUTION_HEIGHT

    def plan(self, vllm_output: VLLMResponse) -> Trajectory:
        """
        根据VLM输出生成轨迹

        Args:
            vllm_output: VLM推理结果

        Returns:
            Trajectory对象
        """
        # 起点：图像下方中间
        start_x = self.image_width // 2
        start_y = self.image_height - 20  # 距离底部20像素

        # 目标点：根据VLM的goal_direction计算
        goal_dir = vllm_output.goal_direction
        azimuth = np.deg2rad(goal_dir.get("azimuth", 0))  # 方位角（度转弧度）
        distance = goal_dir.get("distance", 3.0)  # 距离（米）

        # 将实际距离映射到图像像素（简化映射：1米 ≈ 100像素）
        pixel_distance = min(distance * 100, self.image_height * 0.7)

        # 计算终点坐标（图像坐标系：y轴向下，x轴向右）
        end_x = start_x + int(pixel_distance * np.sin(azimuth))
        end_y = start_y - int(pixel_distance * np.cos(azimuth))

        # 限制终点在图像内
        end_x = np.clip(end_x, 20, self.image_width - 20)
        end_y = np.clip(end_y, 20, self.image_height - 20)

        # 生成贝塞尔曲线航点
        waypoints = self._generate_bezier_waypoints(
            (start_x, start_y), (end_x, end_y), distance
        )

        # 计算速度指令
        v, w = self._compute_velocity(waypoints, vllm_output.obstacles)

        return Trajectory(
            waypoints=waypoints,
            v=v,
            w=w,
            confidence=vllm_output.confidence,
        )

    def _generate_bezier_waypoints(
        self, start: Tuple[int, int], end: Tuple[int, int], real_distance: float
    ) -> list:
        """生成平滑贝塞尔曲线航点"""
        start_x, start_y = start
        end_x, end_y = end

        # 控制点设计（略微向上弯曲，避免突兀）
        dx = end_x - start_x
        dy = end_y - start_y

        # 控制点1：起点向目标方向30%
        ctrl1_x = start_x + 0.3 * dx
        ctrl1_y = start_y + 0.3 * dy - 30  # 向上偏移

        # 控制点2：起点向目标方向70%
        ctrl2_x = start_x + 0.7 * dx
        ctrl2_y = start_y + 0.7 * dy - 20

        # 贝塞尔曲线参数化
        t = np.linspace(0, 1, self.num_waypoints)
        points = []

        for ti in t:
            # 三次贝塞尔曲线公式
            x = (
                (1 - ti) ** 3 * start_x
                + 3 * (1 - ti) ** 2 * ti * ctrl1_x
                + 3 * (1 - ti) * ti**2 * ctrl2_x
                + ti**3 * end_x
            )
            y = (
                (1 - ti) ** 3 * start_y
                + 3 * (1 - ti) ** 2 * ti * ctrl1_y
                + 3 * (1 - ti) * ti**2 * ctrl2_y
                + ti**3 * end_y
            )

            # 计算相对距离（用于颜色映射）
            relative_dist = ti * real_distance

            points.append(Waypoint(x=float(x), y=float(y), distance=relative_dist))

        return points

    def _compute_velocity(self, waypoints: list, obstacles: list) -> Tuple[float, float]:
        """
        计算线速度和角速度（动态窗口法简化版）

        Args:
            waypoints: 航点列表
            obstacles: 障碍物列表

        Returns:
            (v, w) 线速度和角速度
        """
        if not waypoints or len(waypoints) < 2:
            return 0.0, 0.0

        # 第一个航点（执行目标）
        first_wp = waypoints[0]
        second_wp = waypoints[1] if len(waypoints) > 1 else waypoints[0]

        # 计算方向角
        dx = second_wp.x - first_wp.x
        dy = second_wp.y - first_wp.y
        target_angle = np.arctan2(dx, -dy)  # 图像坐标系y轴向下

        # 计算距离（像素转米）
        pixel_dist = np.sqrt(dx**2 + dy**2)
        meter_dist = pixel_dist / 100.0  # 1米 ≈ 100像素

        # 基础线速度（根据距离调整）
        v = min(self.max_v, meter_dist / 2.0)

        # 根据障碍物调整速度
        for obs in obstacles:
            obs_dist = obs.get("distance", 10.0)
            if obs_dist < 1.0:  # 距离障碍物<1米，减速
                v *= 0.5
            if obs_dist < 0.5:  # 非常近，停止
                v = 0.1

        # 角速度（根据方向偏差）
        w = np.clip(target_angle * 0.5, -self.max_w, self.max_w)

        # 如果到达目标（VLM判断），停止
        if meter_dist < 0.3:
            v = 0.0
            w = 0.0

        return float(v), float(w)
