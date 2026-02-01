"""测试推理流水线（latest-frame-only + stop 立即生效）"""

import asyncio

from backend.models.navigation import VLLMResponse
from backend.models.trajectory import Trajectory, Waypoint
from backend.websocket.inference_pipeline import InferencePipeline


class FakeVLLMClient:
    def __init__(self, delay_s: float = 0.0):
        self.delay_s = delay_s
        self.calls = []

    async def analyze_frame_b64(self, frame_b64: str, instruction: str, memory: str = ""):
        self.calls.append({"frame_b64": frame_b64, "instruction": instruction, "memory": memory})
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        return VLLMResponse(
            spatial_analysis="ok",
            action="move_forward",
            goal_direction={"azimuth": 0, "distance": 3.0},
            obstacles=[],
            confidence=0.9,
            reached_goal=False,
        )


class FakePlanner:
    def plan(self, _vllm_result):
        return Trajectory(
            waypoints=[
                Waypoint(x=10, y=10, distance=0.0),
                Waypoint(x=20, y=20, distance=1.0),
            ],
            v=0.5,
            w=0.1,
            confidence=0.9,
        )


async def _wait_until(predicate, timeout_s: float = 1.0):
    loop = asyncio.get_running_loop()
    start = loop.time()
    while True:
        if predicate():
            return
        if loop.time() - start > timeout_s:
            raise TimeoutError("timeout")
        await asyncio.sleep(0.01)


async def test_latest_frame_only_discards_stale_inflight_result():
    messages = []

    async def send_to_client(client_id: str, message: dict):
        messages.append((client_id, message))

    vllm = FakeVLLMClient(delay_s=0.05)
    pipeline = InferencePipeline(
        send_to_client=send_to_client,
        get_db=lambda: None,
        vllm_client=vllm,
        path_planner=FakePlanner(),
    )

    await pipeline.bind_task(task_id="t1", client_id="c1")

    await pipeline.submit_frame(
        task_id="t1",
        client_id="c1",
        frame_b64="frame1",
        frame_seq=1,
        timestamp_ms=1,
        instruction="go",
    )
    await asyncio.sleep(0.01)
    await pipeline.submit_frame(
        task_id="t1",
        client_id="c1",
        frame_b64="frame2",
        frame_seq=2,
        timestamp_ms=2,
        instruction="go",
    )

    await _wait_until(lambda: any(m[1].get("type") == "navigation_update" for m in messages), timeout_s=1.0)
    updates = [m[1] for m in messages if m[1].get("type") == "navigation_update"]
    assert len(updates) == 1
    assert updates[0]["frame_seq"] == 2

    await pipeline.stop_task("t1")


async def test_stop_task_cancels_and_no_more_updates():
    messages = []

    async def send_to_client(client_id: str, message: dict):
        messages.append((client_id, message))

    vllm = FakeVLLMClient(delay_s=0.2)
    pipeline = InferencePipeline(
        send_to_client=send_to_client,
        get_db=lambda: None,
        vllm_client=vllm,
        path_planner=FakePlanner(),
    )

    await pipeline.bind_task(task_id="t2", client_id="c1")
    await pipeline.submit_frame(
        task_id="t2",
        client_id="c1",
        frame_b64="frame1",
        frame_seq=1,
        timestamp_ms=1,
        instruction="go",
    )

    await asyncio.sleep(0.05)
    await pipeline.stop_task("t2")
    await asyncio.sleep(0.3)

    updates = [m[1] for m in messages if m[1].get("type") == "navigation_update"]
    assert updates == []
