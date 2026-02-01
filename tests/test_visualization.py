"""测试可视化功能"""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.trajectory import Trajectory, Waypoint
from backend.utils.visualization import draw_trajectory_on_frame, interpolate_color


def test_color_interpolation():
    """测试颜色插值"""
    print("=== 测试颜色插值 ===\n")

    # 近处 → 绿色
    color = interpolate_color(0, 5.0)
    print(f"距离0 (BGR): {color}")
    assert color == (0, 255, 0), "距离0应为纯绿色"

    # 中间 → 黄色
    color = interpolate_color(2.5, 5.0)
    print(f"距离2.5 (BGR): {color}")
    assert color[2] == 255, "中间距离红色通道应为255"
    assert color[1] == 255, "中间距离绿色通道应为255"

    # 远处 → 红色
    color = interpolate_color(5.0, 5.0)
    print(f"距离5.0 (BGR): {color}")
    assert color == (0, 0, 255), "最大距离应为纯红色"

    print("✓ 颜色插值正确！\n")


def test_trajectory_visualization():
    """测试轨迹绘制"""
    print("=== 测试轨迹绘制 ===\n")

    # 创建测试帧（黑色背景）
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 创建测试轨迹
    waypoints = [
        Waypoint(x=320 + i * 10, y=460 - i * 30, distance=i * 0.5)
        for i in range(12)
    ]

    trajectory = Trajectory(
        waypoints=waypoints,
        v=0.5,
        w=0.2,
        confidence=0.85,
    )

    # 绘制轨迹
    result = draw_trajectory_on_frame(frame, trajectory)

    assert result.shape == frame.shape, "输出帧尺寸应与输入一致"
    assert result.dtype == np.uint8, "输出帧应为uint8类型"

    # 检查是否有像素被修改（绘制了内容）
    assert not np.array_equal(result, frame), "输出帧应与输入帧不同"

    # 保存测试图像
    output_path = Path(__file__).parent.parent / "data" / "test_trajectory.jpg"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), result)
    print(f"✓ 轨迹图像已保存: {output_path}")

    print("✅ 可视化测试通过！")


if __name__ == "__main__":
    test_color_interpolation()
    test_trajectory_visualization()
