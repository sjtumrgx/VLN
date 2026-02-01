"""测试路径规划算法"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.path_planner import PathPlanner
from backend.models.navigation import VLLMResponse


def test_path_planning():
    """测试路径规划功能"""
    print("=== 测试路径规划 ===\n")

    planner = PathPlanner()

    # 模拟VLM输出
    vllm_output = VLLMResponse(
        spatial_analysis="前方开阔，目标在右前方约3米处",
        action="move_forward",
        goal_direction={"azimuth": 30, "distance": 3.0},
        obstacles=[
            {"type": "wall", "position": "left", "distance": 2.0}
        ],
        confidence=0.85,
        reached_goal=False,
    )

    # 生成轨迹
    trajectory = planner.plan(vllm_output)

    print(f"✓ 航点数量: {len(trajectory.waypoints)}")
    assert 10 <= len(trajectory.waypoints) <= 15, "航点数量应在10-15之间"

    print(f"✓ 线速度 v: {trajectory.v:.3f} m/s")
    assert 0 <= trajectory.v <= 1.0, "线速度应在0-1.0之间"

    print(f"✓ 角速度 w: {trajectory.w:.3f} rad/s")
    assert -1.57 <= trajectory.w <= 1.57, "角速度应在-π/2到π/2之间"

    print(f"✓ 置信度: {trajectory.confidence:.3f}")
    assert trajectory.confidence == 0.85, "置信度应与输入一致"

    print(f"\n第一个航点: x={trajectory.waypoints[0].x:.1f}, y={trajectory.waypoints[0].y:.1f}")
    print(f"最后航点: x={trajectory.waypoints[-1].x:.1f}, y={trajectory.waypoints[-1].y:.1f}")

    print("\n✅ 路径规划测试通过！")


def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===\n")

    planner = PathPlanner()

    # 测试1: 极近目标
    print("测试1: 极近目标")
    vllm_output = VLLMResponse(
        spatial_analysis="已接近目标",
        action="move_forward",
        goal_direction={"azimuth": 0, "distance": 0.2},
        obstacles=[],
        confidence=0.9,
    )
    trajectory = planner.plan(vllm_output)
    print(f"  v={trajectory.v:.3f}, w={trajectory.w:.3f}")
    assert trajectory.v < 0.5, "接近目标时应减速"

    # 测试2: 大角度转向
    print("测试2: 大角度转向")
    vllm_output = VLLMResponse(
        spatial_analysis="目标在左侧",
        action="turn_left",
        goal_direction={"azimuth": -60, "distance": 5.0},
        obstacles=[],
        confidence=0.8,
    )
    trajectory = planner.plan(vllm_output)
    print(f"  v={trajectory.v:.3f}, w={trajectory.w:.3f}")
    assert abs(trajectory.w) > 0.3, "大角度转向时角速度应较大"

    # 测试3: 近距离障碍物
    print("测试3: 近距离障碍物")
    vllm_output = VLLMResponse(
        spatial_analysis="前方有障碍",
        action="move_forward",
        goal_direction={"azimuth": 0, "distance": 3.0},
        obstacles=[
            {"type": "obstacle", "position": "front", "distance": 0.3}
        ],
        confidence=0.7,
    )
    trajectory = planner.plan(vllm_output)
    print(f"  v={trajectory.v:.3f}, w={trajectory.w:.3f}")
    assert trajectory.v < 0.3, "近距离障碍物时应大幅减速"

    print("\n✅ 边界情况测试通过！")


if __name__ == "__main__":
    test_path_planning()
    test_edge_cases()
