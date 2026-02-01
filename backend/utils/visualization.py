"""Visualization utilities for trajectory overlay"""

import cv2
import numpy as np

from backend.models.trajectory import Trajectory


def interpolate_color(distance: float, max_dist: float) -> tuple:
    """
    根据距离计算颜色（绿色→黄色→红色）

    Args:
        distance: 当前距离
        max_dist: 最大距离

    Returns:
        (B, G, R) BGR颜色元组
    """
    if max_dist == 0:
        return (0, 255, 0)  # 默认绿色

    ratio = distance / max_dist

    if ratio < 0.5:
        # 绿色 → 黄色
        g = 255
        r = int(255 * ratio * 2)
        b = 0
    else:
        # 黄色 → 红色
        g = int(255 * (1 - (ratio - 0.5) * 2))
        r = 255
        b = 0

    return (b, g, r)


def draw_trajectory_on_frame(frame: np.ndarray, trajectory: Trajectory) -> np.ndarray:
    """
    在视频帧上绘制轨迹

    Args:
        frame: 输入视频帧 (BGR)
        trajectory: 轨迹对象

    Returns:
        绘制后的帧
    """
    overlay = frame.copy()
    waypoints = trajectory.waypoints
    max_dist = trajectory.max_distance

    # 绘制轨迹曲线
    for i in range(len(waypoints) - 1):
        wp1 = waypoints[i]
        wp2 = waypoints[i + 1]

        # 计算颜色
        color = interpolate_color(wp1.distance, max_dist)

        # 绘制线段
        cv2.line(
            overlay,
            (int(wp1.x), int(wp1.y)),
            (int(wp2.x), int(wp2.y)),
            color,
            thickness=4,
            lineType=cv2.LINE_AA,
        )

    # 绘制航点圆点
    for wp in waypoints:
        color = interpolate_color(wp.distance, max_dist)
        cv2.circle(overlay, (int(wp.x), int(wp.y)), radius=3, color=color, thickness=-1)

    # 高亮第一个航点（执行目标）
    first_wp = waypoints[0]
    cv2.circle(
        overlay,
        (int(first_wp.x), int(first_wp.y)),
        radius=10,
        color=(0, 255, 255),  # 黄色
        thickness=2,
    )
    cv2.circle(
        overlay,
        (int(first_wp.x), int(first_wp.y)),
        radius=5,
        color=(0, 255, 255),
        thickness=-1,
    )

    # 绘制起点标记
    start_x = frame.shape[1] // 2
    start_y = frame.shape[0] - 20
    cv2.circle(overlay, (start_x, start_y), radius=8, color=(255, 255, 255), thickness=2)

    # 绘制v, w信息（带半透明背景）
    info_bg = overlay.copy()
    cv2.rectangle(info_bg, (5, 5), (250, 90), (0, 0, 0), -1)
    cv2.addWeighted(info_bg, 0.5, overlay, 0.5, 0, overlay)

    cv2.putText(
        overlay,
        f"v: {trajectory.v:.2f} m/s",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        overlay,
        f"w: {trajectory.w:.2f} rad/s",
        (10, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )

    # 显示置信度
    confidence_color = (0, 255, 0) if trajectory.confidence > 0.7 else (0, 165, 255)
    cv2.putText(
        overlay,
        f"Conf: {trajectory.confidence:.2f}",
        (10, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        confidence_color,
        2,
        cv2.LINE_AA,
    )

    # 半透明叠加
    result = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)

    return result
