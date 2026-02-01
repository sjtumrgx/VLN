"""回归测试：PathPlanner 不应误判到达导致 v/w=0"""

from backend.models.navigation import VLLMResponse
from backend.services.path_planner import PathPlanner


def test_plan_velocity_positive_when_not_reached_goal():
    planner = PathPlanner()
    traj = planner.plan(
        VLLMResponse(
            goal_direction={"azimuth": 0, "distance": 3.0},
            obstacles=[],
            confidence=0.9,
            reached_goal=False,
        )
    )
    assert traj.v > 0.0


def test_plan_velocity_zero_when_reached_goal():
    planner = PathPlanner()
    traj = planner.plan(
        VLLMResponse(
            goal_direction={"azimuth": 0, "distance": 3.0},
            obstacles=[],
            confidence=0.9,
            reached_goal=True,
        )
    )
    assert traj.v == 0.0
    assert traj.w == 0.0


def test_plan_distance_fallback_when_distance_non_positive():
    planner = PathPlanner()
    traj = planner.plan(
        VLLMResponse(
            goal_direction={"azimuth": 0, "distance": 0.0},
            obstacles=[],
            confidence=0.9,
            reached_goal=False,
        )
    )
    assert traj.v > 0.0
