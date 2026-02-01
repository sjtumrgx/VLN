"""回归测试：WebUI黑屏/停止状态问题

说明：
这些测试是“最小防回归”级别，使用静态检查保证关键逻辑不再退回到已知的错误实现：
1) VideoCanvas 不应捕获旧的 currentTask（否则会导致：先加载视频再发布任务/停止任务后仍继续发帧）。
2) 停止任务应使用 stopped 状态，并在任务历史中可视化。
3) 后端 TaskStatus 必须支持 stopped，避免 SQLite 读写解析报错。
"""

from __future__ import annotations

from pathlib import Path


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_backend_task_status_supports_stopped():
    from backend.models.task import TaskStatus

    assert any(s.value == "stopped" for s in TaskStatus), "后端 TaskStatus 缺少 stopped 状态"


def test_frontend_app_stop_uses_stopped_status():
    text = _read_text("frontend/src/App.jsx")
    assert "status: 'stopped'" in text, "前端停止任务应更新 status 为 'stopped'"


def test_frontend_task_history_renders_stopped_status():
    text = _read_text("frontend/src/components/TaskHistory.jsx")
    assert "stopped" in text, "任务历史未配置 stopped 状态显示"


def test_frontend_video_canvas_uses_latest_task_ref():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert "currentTaskRef" in text, "VideoCanvas 应使用 ref 保存最新 currentTask，避免闭包捕获旧值"
    assert (
        "currentTaskRef.current" in text
    ), "VideoCanvas 发送帧/停止逻辑应从 currentTaskRef.current 读取最新任务"


def test_frontend_video_canvas_draws_first_frame_on_video_load():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert "loadeddata" in text, "加载视频后应监听 loadeddata 并绘制首帧到主 Canvas"
    assert (
        "ctx.drawImage(videoRef.current" in text
    ), "首帧预览应使用 ctx.drawImage(videoRef.current, ...) 绘制到主 Canvas"


def test_frontend_task_history_has_stop_button_for_pending_running_only():
    text = _read_text("frontend/src/components/TaskHistory.jsx")
    assert "onStopTask" in text, "TaskHistory 应暴露 onStopTask 回调以支持历史任务停止"
    assert (
        "task.status === 'pending'" in text or "task.status === \"pending\"" in text
    ), "停止按钮应仅对 pending/running 渲染（缺少 pending 判断）"
    assert (
        "task.status === 'running'" in text or "task.status === \"running\"" in text
    ), "停止按钮应仅对 pending/running 渲染（缺少 running 判断）"


def test_frontend_app_wires_task_history_stop_handler():
    text = _read_text("frontend/src/App.jsx")
    assert "onStopTask=" in text, "App 应向 TaskHistory 传入 onStopTask 处理函数"


def test_backend_ws_bind_task_sets_task_running():
    text = _read_text("backend/websocket/video_stream.py")
    assert "bind_task" in text
    assert "update_task" in text, "后端在 bind_task 时应写库更新任务状态"
    assert "TaskStatus.RUNNING" in text, "后端在 bind_task 时应将任务置为 running"


def test_backend_ws_stop_task_stops_pipeline_and_updates_db():
    text = _read_text("backend/websocket/video_stream.py")
    assert "stop_task" in text
    assert "TaskStatus.STOPPED" in text, "后端 stop_task 时应将任务置为 stopped"
    assert "pipeline.stop_task" in text, "后端 stop_task 时应停止推理流水线"


def test_frontend_ws_supports_stop_task_and_frame_seq():
    text = _read_text("frontend/src/services/websocket.js")
    assert "stop_task" in text, "前端应支持发送 stop_task 消息"
    assert "frame_seq" in text, "前端 video_frame 应携带 frame_seq"


def test_frontend_app_sends_stop_task_on_stop():
    text = _read_text("frontend/src/App.jsx")
    assert "wsClient.stopTask" in text, "停止任务时应通过WS通知后端立即停止推理"


def test_frontend_video_canvas_listens_navigation_update():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert "navigation_update" in text, "前端应监听 navigation_update（仅叠加轨迹）"


def test_frontend_app_ignores_updates_for_non_current_task():
    text = _read_text("frontend/src/App.jsx")
    assert "data.task_id" in text, "App 应按 task_id 过滤 WS 更新，避免停止后迟到结果导致 UI“复活”"


def test_frontend_video_canvas_has_inference_backpressure_gate():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert (
        "pendingInferenceRef" in text or "inflight" in text or "inFlight" in text
    ), "VideoCanvas 应具备推理背压（最多 1 个 in-flight），避免 WS 堆积导致 stop_task 延迟"


def test_frontend_video_canvas_preview_loop_does_not_stop_on_frozen_ref():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert (
        "video.readyState >= 2 && !frozenRef.current" in text
        or "!frozenRef.current && video.readyState >= 2" in text
    ), "VideoCanvas 预览循环不应在 frozenRef=true 时直接退出（否则会出现“加载视频要等发布任务才播放”）"


def _slice_between(text: str, start_token: str, end_token: str) -> str:
    start = text.index(start_token)
    end = text.index(end_token, start)
    return text[start:end]


def test_frontend_load_video_shows_first_frame_but_does_not_autoplay_or_infer():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    block = _slice_between(text, "const loadTestVideo", "input.click()")
    assert "ctx.drawImage(videoRef.current" in block, "加载视频应绘制首帧"
    assert "videoRef.current.play()" not in block, "加载视频后不应自动播放（应等待发布任务）"
    assert "startFramePump()" not in block, "加载视频后不应自动启动推理帧泵（应等待发布任务）"
    assert "startPreviewLoop()" not in block, "加载视频后不应自动启动预览循环（应等待发布任务）"


def test_frontend_app_primes_file_video_start_before_await_create_task():
    text = _read_text("frontend/src/App.jsx")
    block = _slice_between(text, "const handleCreateTask", "const handleStopTask")
    prime_idx = block.find("primeFileVideoForTaskStart")
    await_idx = block.find("await api.createTask")
    assert prime_idx != -1, "App 发布任务时应 prime 文件视频播放（方案2）"
    assert await_idx != -1, "App.handleCreateTask 应调用 api.createTask"
    assert (
        prime_idx < await_idx
    ), "primeFileVideoForTaskStart 必须在任何 await 之前调用（否则可能触发 autoplay 限制）"


def test_frontend_video_canvas_exposes_imperative_handle_for_task_start():
    text = _read_text("frontend/src/components/VideoCanvas.jsx")
    assert "useImperativeHandle" in text, "VideoCanvas 应通过 useImperativeHandle 暴露 prime/rollback 方法"
    assert (
        "primeFileVideoForTaskStart" in text
    ), "VideoCanvas 应暴露 primeFileVideoForTaskStart（方案2）"
