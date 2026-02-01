"""Latest-frame-only inference pipeline for WebSocket video stream."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

from backend.models.task import TaskStatus
from backend.services.path_planner import PathPlanner
from backend.services.vllm_client import VLLMClient
from backend.storage.sqlite_client import SQLiteClient

logger = logging.getLogger(__name__)

SendToClientFn = Callable[[str, dict], Awaitable[None]]
GetDbFn = Callable[[], Optional[SQLiteClient]]


@dataclass(slots=True)
class FrameInput:
    frame_b64: str
    frame_seq: int
    timestamp_ms: int
    instruction: str


@dataclass
class TaskState:
    task_id: str
    client_id: str
    latest: Optional[FrameInput] = None
    frame_event: asyncio.Event = field(default_factory=asyncio.Event)
    stop_event: asyncio.Event = field(default_factory=asyncio.Event)
    worker: Optional[asyncio.Task] = None
    last_sent_at: float = 0.0
    last_saved_at: float = 0.0
    memory_summary: str = ""


class InferencePipeline:
    """每个 task 只处理最新帧，避免积压；停止后丢弃 in-flight 结果。"""

    def __init__(
        self,
        *,
        send_to_client: SendToClientFn,
        get_db: GetDbFn,
        vllm_client: Optional[VLLMClient] = None,
        path_planner: Optional[PathPlanner] = None,
    ):
        self._send_to_client = send_to_client
        self._get_db = get_db

        self._tasks: Dict[str, TaskState] = {}
        self._lock = asyncio.Lock()

        self._vllm = vllm_client or VLLMClient()
        self._planner = path_planner or PathPlanner()

    async def bind_task(self, *, task_id: str, client_id: str):
        async with self._lock:
            state = self._tasks.get(task_id)
            if state:
                state.client_id = client_id
            else:
                state = TaskState(task_id=task_id, client_id=client_id)
                self._tasks[task_id] = state

            if state.worker is None or state.worker.done():
                state.stop_event.clear()
                state.worker = asyncio.create_task(self._run_task(state))

    async def submit_frame(
        self,
        *,
        task_id: str,
        client_id: str,
        frame_b64: str,
        frame_seq: int,
        timestamp_ms: int,
        instruction: str,
    ):
        async with self._lock:
            state = self._tasks.get(task_id)
            if not state:
                # 未 bind_task 时不创建 worker，避免无意义的后台任务
                return

            # client_id 可能会变化（重连）
            state.client_id = client_id
            state.latest = FrameInput(
                frame_b64=frame_b64,
                frame_seq=frame_seq,
                timestamp_ms=timestamp_ms,
                instruction=instruction,
            )
            state.frame_event.set()

    async def stop_task(self, task_id: str):
        async with self._lock:
            state = self._tasks.pop(task_id, None)

        if not state:
            return

        state.stop_event.set()
        if state.worker and not state.worker.done():
            state.worker.cancel()
            try:
                await state.worker
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("stop_task: worker异常退出")

    async def disconnect_client(self, client_id: str):
        async with self._lock:
            task_ids = [tid for tid, st in self._tasks.items() if st.client_id == client_id]

        for task_id in task_ids:
            await self.stop_task(task_id)

    async def _run_task(self, state: TaskState):
        last_seen_seq = -1
        while not state.stop_event.is_set():
            await state.frame_event.wait()
            state.frame_event.clear()

            if state.stop_event.is_set():
                break

            snapshot = state.latest
            if not snapshot:
                continue

            if snapshot.frame_seq == last_seen_seq:
                continue
            last_seen_seq = snapshot.frame_seq

            started = time.monotonic()
            vllm_result = await self._vllm.analyze_frame_b64(
                snapshot.frame_b64,
                instruction=snapshot.instruction,
                memory=state.memory_summary,
            )
            inference_ms = (time.monotonic() - started) * 1000.0

            if state.stop_event.is_set():
                break

            # 若推理期间来了新帧，则丢弃旧结果（保证轨迹尽量贴近当前画面）
            latest = state.latest
            if latest and latest.frame_seq != snapshot.frame_seq:
                continue

            if vllm_result is None:
                await self._send_update(
                    state=state,
                    frame_seq=snapshot.frame_seq,
                    timestamp_ms=snapshot.timestamp_ms,
                    inference_ms=inference_ms,
                    payload={
                        "error": "vLLM inference failed",
                        "waypoints": [],
                        "v": 0.0,
                        "w": 0.0,
                        "confidence": 0.0,
                        "reached_goal": False,
                    },
                )
                continue

            trajectory = self._planner.plan(vllm_result)

            await self._send_update(
                state=state,
                frame_seq=snapshot.frame_seq,
                timestamp_ms=snapshot.timestamp_ms,
                inference_ms=inference_ms,
                payload={
                    "waypoints": [
                        {"x": wp.x, "y": wp.y, "distance": wp.distance}
                        for wp in trajectory.waypoints
                    ],
                    "v": trajectory.v,
                    "w": trajectory.w,
                    "confidence": trajectory.confidence,
                    "reached_goal": vllm_result.reached_goal,
                },
            )

            await self._maybe_persist(state.task_id, trajectory)

    async def _send_update(
        self,
        *,
        state: TaskState,
        frame_seq: int,
        timestamp_ms: int,
        inference_ms: float,
        payload: dict,
    ):
        now_ms = int(time.time() * 1000)
        latency_ms = now_ms - timestamp_ms if timestamp_ms else 0

        fps = 0.0
        now_mono = time.monotonic()
        if state.last_sent_at:
            delta = now_mono - state.last_sent_at
            if delta > 0:
                fps = 1.0 / delta
        state.last_sent_at = now_mono

        message = {
            "type": "navigation_update",
            "task_id": state.task_id,
            "frame_seq": frame_seq,
            "timestamp": now_ms,
            "latency": latency_ms,
            "inference_ms": round(inference_ms, 2),
            "fps": fps,
            **payload,
        }

        try:
            await self._send_to_client(state.client_id, message)
        except Exception:
            logger.exception("发送 navigation_update 失败")

    async def _maybe_persist(self, task_id: str, trajectory):
        db = self._get_db()
        if not db:
            return

        now = time.monotonic()

        # 节流：避免每帧写库拖慢推理链路
        state = self._tasks.get(task_id)
        if state and now - state.last_saved_at < 1.0:
            return

        try:
            await db.save_trajectory(task_id, trajectory)
            if state:
                state.last_saved_at = now
        except Exception:
            logger.exception("保存轨迹失败")


async def set_task_status(db: Optional[SQLiteClient], task_id: str, status: TaskStatus):
    if not db:
        return
    await db.update_task(task_id, {"status": status})
