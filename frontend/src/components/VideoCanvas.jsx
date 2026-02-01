import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'

function interpolateColor(distance, maxDist) {
  if (!maxDist) return 'rgb(0, 255, 0)'
  const ratio = distance / maxDist
  if (ratio < 0.5) {
    const r = Math.floor(255 * ratio * 2)
    return `rgb(${r}, 255, 0)`
  }
  const g = Math.floor(255 * (1 - (ratio - 0.5) * 2))
  return `rgb(255, ${g}, 0)`
}

function drawTrajectory(ctx, waypoints, width, height) {
  ctx.clearRect(0, 0, width, height)
  if (!waypoints || waypoints.length < 2) return

  const maxDist = waypoints[waypoints.length - 1]?.distance || 0

  // 轨迹线段
  ctx.lineWidth = 4
  ctx.lineCap = 'round'
  for (let i = 0; i < waypoints.length - 1; i++) {
    const wp1 = waypoints[i]
    const wp2 = waypoints[i + 1]
    ctx.strokeStyle = interpolateColor(wp1.distance, maxDist)
    ctx.beginPath()
    ctx.moveTo(wp1.x, wp1.y)
    ctx.lineTo(wp2.x, wp2.y)
    ctx.stroke()
  }

  // 航点圆点
  for (const wp of waypoints) {
    ctx.fillStyle = interpolateColor(wp.distance, maxDist)
    ctx.beginPath()
    ctx.arc(wp.x, wp.y, 3, 0, Math.PI * 2)
    ctx.fill()
  }

  // 高亮第一个航点
  const first = waypoints[0]
  ctx.strokeStyle = 'rgb(255, 255, 0)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(first.x, first.y, 10, 0, Math.PI * 2)
  ctx.stroke()
  ctx.fillStyle = 'rgb(255, 255, 0)'
  ctx.beginPath()
  ctx.arc(first.x, first.y, 5, 0, Math.PI * 2)
  ctx.fill()

  // 起点标记
  const startX = width / 2
  const startY = height - 20
  ctx.strokeStyle = 'rgb(255, 255, 255)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(startX, startY, 8, 0, Math.PI * 2)
  ctx.stroke()
}

const VideoCanvas = forwardRef(function VideoCanvas({ wsClient, currentTask, stats, freezeSignal = 0 }, ref) {
  const canvasRef = useRef(null)
  const overlayCanvasRef = useRef(null)
  const videoRef = useRef(null)
  const currentTaskRef = useRef(currentTask)
  const videoObjectUrlRef = useRef(null)
  const firstFrameRef = useRef(null)
  const captureCanvasRef = useRef(null)
  const frameSeqRef = useRef(0)
  const lastAppliedSeqRef = useRef(-1)
  const isEncodingRef = useRef(false)
  const pendingInferenceRef = useRef(false)
  const rafIdRef = useRef(null)
  const frozenRef = useRef(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isFrozen, setIsFrozen] = useState(false)
  const [frameCount, setFrameCount] = useState(0)
  const streamIntervalRef = useRef(null)

  useEffect(() => {
    currentTaskRef.current = currentTask
  }, [currentTask])

  useEffect(() => {
    frozenRef.current = isFrozen
  }, [isFrozen])

  const [backendConfig, setBackendConfig] = useState(null)
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/health/config')
        if (!res.ok) return
        const data = await res.json()
        setBackendConfig(data)
      } catch (_) {
        // ignore
      }
    }
    fetchConfig()
  }, [])

  const videoResolution = useMemo(() => {
    const fallback = { width: 480, height: 360 }
    if (!backendConfig?.video_resolution) return fallback
    const [width, height] = backendConfig.video_resolution
    if (!width || !height) return fallback
    return { width, height }
  }, [backendConfig])

  const inferenceFps = backendConfig?.inference_fps || 5
  const jpegQuality = backendConfig?.vllm_image_jpeg_quality || 70

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const handleNavUpdate = (data) => {
      if (frozenRef.current) return
      const task = currentTaskRef.current
      if (!task || data.task_id !== task.id) return
      pendingInferenceRef.current = false

      const seq = typeof data.frame_seq === 'number' ? data.frame_seq : parseInt(data.frame_seq || '0', 10)
      if (Number.isFinite(seq) && seq <= lastAppliedSeqRef.current) return
      lastAppliedSeqRef.current = Number.isFinite(seq) ? seq : lastAppliedSeqRef.current

      const overlay = overlayCanvasRef.current
      if (!overlay) return
      const ctx = overlay.getContext('2d')
      drawTrajectory(ctx, data.waypoints || [], overlay.width, overlay.height)
      setFrameCount(prev => prev + 1)
    }

    wsClient.on('navigation_update', handleNavUpdate)

    return () => {
      wsClient.off('navigation_update', handleNavUpdate)
    }
  }, [wsClient])

  const stopFramePump = () => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current)
      streamIntervalRef.current = null
    }
  }

  const startPreviewLoop = () => {
    if (rafIdRef.current) return
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video) return

    const ctx = canvas.getContext('2d')
    const draw = () => {
      if (video.readyState >= 2 && !frozenRef.current) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
      }
      rafIdRef.current = requestAnimationFrame(draw)
    }
    rafIdRef.current = requestAnimationFrame(draw)
  }

  const stopPreviewLoop = () => {
    if (!rafIdRef.current) return
    cancelAnimationFrame(rafIdRef.current)
    rafIdRef.current = null
  }

  const startFramePump = () => {
    stopFramePump()

    const intervalMs = Math.max(50, Math.floor(1000 / Math.max(1, inferenceFps)))
    streamIntervalRef.current = setInterval(() => {
      const task = currentTaskRef.current
      const video = videoRef.current
      if (!task || !video || video.readyState < 2) return
      if (!wsClient.isConnected) return
      if (!wsClient.ws) return

      // 推理背压：最多 1 个 in-flight（避免 WS 堆积导致 stop_task 延迟）
      if (pendingInferenceRef.current) return

      // 浏览器端背压：WS缓冲区过大时丢帧（避免堆积导致“停止后又动”）
      if (wsClient.ws.bufferedAmount > 256 * 1024) return

      // 编码仍在进行：丢帧（latest-frame-only）
      if (isEncodingRef.current) return
      isEncodingRef.current = true

      if (!captureCanvasRef.current) {
        const canvas = document.createElement('canvas')
        canvas.width = videoResolution.width
        canvas.height = videoResolution.height
        captureCanvasRef.current = canvas
      }

      const captureCtx = captureCanvasRef.current.getContext('2d')
      captureCtx.drawImage(videoRef.current, 0, 0, videoResolution.width, videoResolution.height)

      captureCanvasRef.current.toBlob((blob) => {
        if (!blob) {
          isEncodingRef.current = false
          return
        }
        const reader = new FileReader()
        reader.onloadend = () => {
          const latestTask = currentTaskRef.current
          if (!latestTask || latestTask.id !== task.id) {
            isEncodingRef.current = false
            return
          }
          const base64 = reader.result.split(',')[1]
          const seq = frameSeqRef.current++
          wsClient.sendVideoFrame(base64, task.id, task.instruction, seq)
          pendingInferenceRef.current = true
          isEncodingRef.current = false
        }
        reader.readAsDataURL(blob)
      }, 'image/jpeg', Math.min(0.95, Math.max(0.3, jpegQuality / 100)))
    }, intervalMs)
  }

  const startVideoStream = async () => {
    try {
      setIsFrozen(false)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: videoResolution.width, height: videoResolution.height }
      })

      if (videoRef.current) {
        videoRef.current.ontimeupdate = null
        videoRef.current.onended = null
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }

      setIsStreaming(true)
      startFramePump()
      startPreviewLoop()
    } catch (err) {
      console.error('无法访问摄像头:', err)
      alert('无法访问摄像头，请检查权限设置')
    }
  }

  const stopVideoStream = () => {
    stopFramePump()
    stopPreviewLoop()
    pendingInferenceRef.current = false

    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current)
      streamIntervalRef.current = null
    }

    if (videoRef.current) {
      videoRef.current.ontimeupdate = null
      videoRef.current.onended = null

      if (videoRef.current.srcObject) {
        const stream = videoRef.current.srcObject
        stream.getTracks().forEach(track => track.stop())
        videoRef.current.srcObject = null
      }

      if (videoRef.current.src) {
        videoRef.current.pause()
        videoRef.current.removeAttribute('src')
        videoRef.current.load()
      }
    }

    if (videoObjectUrlRef.current) {
      URL.revokeObjectURL(videoObjectUrlRef.current)
      videoObjectUrlRef.current = null
    }

    setIsStreaming(false)
    setIsFrozen(false)
  }

  const loadTestVideo = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'video/*'
    input.onchange = (e) => {
      const file = e.target.files[0]
      if (file && videoRef.current) {
        setIsFrozen(false)
        stopVideoStream()
        if (videoObjectUrlRef.current) {
          URL.revokeObjectURL(videoObjectUrlRef.current)
        }
        const url = URL.createObjectURL(file)
        videoObjectUrlRef.current = url
        videoRef.current.src = url
        videoRef.current.addEventListener('loadeddata', () => {
          const canvas = canvasRef.current
          if (!canvas || !videoRef.current) return
          const ctx = canvas.getContext('2d')
          ctx.clearRect(0, 0, canvas.width, canvas.height)
          ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height)

          // 缓存首帧用于失败回滚：回到“首帧暂停等待任务”状态
          try {
            firstFrameRef.current = ctx.getImageData(0, 0, canvas.width, canvas.height)
          } catch (_) {
            firstFrameRef.current = null
          }

          // 本地文件视频：加载后保持暂停，等待发布任务用户手势触发播放（方案2）
          videoRef.current.pause()
        }, { once: true })
        setIsStreaming(true)
      }
    }
    input.click()
  }

  const isFileVideo = () => {
    const video = videoRef.current
    if (!video) return false
    return Boolean(videoObjectUrlRef.current && video.src && !video.srcObject)
  }

  const restoreFirstFrame = () => {
    const canvas = canvasRef.current
    if (!canvas) return
    const firstFrame = firstFrameRef.current
    if (!firstFrame) return
    const ctx = canvas.getContext('2d')
    ctx.putImageData(firstFrame, 0, 0)
  }

  const primeFileVideoForTaskStart = () => {
    if (!isFileVideo()) return

    // 解除冻结（停止任务后）并开始预览循环
    frozenRef.current = false
    setIsFrozen(false)
    startPreviewLoop()

    // 用户手势中触发播放（避免 autoplay 限制）
    const video = videoRef.current
    if (!video) return
    if (!video.paused) return
    const p = video.play()
    if (p && typeof p.catch === 'function') {
      p.catch((err) => {
        console.warn('文件视频播放被浏览器拦截或失败:', err)
      })
    }
  }

  const rollbackFileVideoToFirstFrame = () => {
    if (!isFileVideo()) return
    const video = videoRef.current
    if (video) video.pause()
    pendingInferenceRef.current = false
    stopFramePump()
    stopPreviewLoop()
    restoreFirstFrame()
  }

  useImperativeHandle(ref, () => ({
    primeFileVideoForTaskStart,
    rollbackFileVideoToFirstFrame,
  }))

  // 停止当前任务：冻结画面（保留最后一帧），并确保不再继续发送帧
  useEffect(() => {
    if (!freezeSignal) return
    setIsFrozen(true)
    if (isFileVideo() && videoRef.current) {
      videoRef.current.pause()
    }
    pendingInferenceRef.current = false
    stopFramePump()
    stopPreviewLoop()
  }, [freezeSignal])

  // 发布新任务：解冻并恢复预览/帧泵
  useEffect(() => {
    if (!currentTask) return
    setIsFrozen(false)
    frameSeqRef.current = 0
    lastAppliedSeqRef.current = -1
    pendingInferenceRef.current = false
    const overlay = overlayCanvasRef.current
    if (overlay) {
      const ctx = overlay.getContext('2d')
      ctx.clearRect(0, 0, overlay.width, overlay.height)
    }
    startFramePump()
    startPreviewLoop()
  }, [currentTask])

  useEffect(() => {
    return () => {
      stopVideoStream()
    }
  }, [])

  return (
    <motion.div
      className="glass rounded-2xl p-4 h-full flex flex-col corner-brackets relative overflow-hidden"
      initial={{ scale: 0.95 }}
      animate={{ scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Scan line effect */}
      <div className="scan-lines absolute inset-0 pointer-events-none" />

      {/* Title */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-display font-bold tracking-wider text-cyan-400 uppercase">
          视觉输入
        </h2>
        <div className="flex gap-2">
          <button
            onClick={isStreaming ? stopVideoStream : startVideoStream}
            className={`px-3 py-1 text-xs font-mono rounded border transition-all ${
              isStreaming
                ? 'bg-red-500/20 border-red-500 text-red-400 hover:bg-red-500/30'
                : 'bg-cyan-500/20 border-cyan-500 text-cyan-400 hover:bg-cyan-500/30'
            }`}
          >
            {isStreaming ? '停止摄像头' : '启动摄像头'}
          </button>
          <button
            onClick={loadTestVideo}
            className="px-3 py-1 text-xs font-mono rounded border bg-blue-500/20 border-blue-500 text-blue-400 hover:bg-blue-500/30 transition-all"
          >
            加载视频
          </button>
        </div>
      </div>

      {/* Video Display */}
      <div className="flex-1 bg-black/40 rounded-lg overflow-hidden relative border border-cyan-500/20">
        <canvas
          ref={canvasRef}
          width={videoResolution.width}
          height={videoResolution.height}
          className="absolute inset-0 w-full h-full object-contain"
        />
        <canvas
          ref={overlayCanvasRef}
          width={videoResolution.width}
          height={videoResolution.height}
          className="absolute inset-0 w-full h-full object-contain pointer-events-none"
        />
        <video
          ref={videoRef}
          className="hidden"
          muted
          playsInline
        />

        {/* Overlay Info */}
        {!isStreaming && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto mb-4 border-2 border-cyan-500/30 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-cyan-500/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <p className="text-gray-400 font-mono text-sm">等待视频输入</p>
            </div>
          </div>
        )}

        {isFrozen && (
          <div className="absolute right-3 top-3 px-2 py-1 bg-gray-900/60 border border-gray-500/40 rounded text-xs font-mono text-gray-200">
            已冻结（停止任务）
          </div>
        )}
      </div>

      {/* Stats Bar */}
      <div className="mt-3 flex items-center justify-between px-4 py-2 bg-black/30 rounded-lg border border-cyan-500/10">
        <div className="flex items-center gap-6 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="text-gray-500">FPS:</span>
            <span className="text-cyan-400 font-semibold">{stats.fps.toFixed(1)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">延迟:</span>
            <span className="text-cyan-400 font-semibold">{stats.latency}ms</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">推理:</span>
            <span className="text-cyan-400 font-semibold">{stats.inferenceMs || 0}ms</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-500">帧数:</span>
            <span className="text-cyan-400 font-semibold">{frameCount}</span>
          </div>
        </div>
        <div className="text-xs text-gray-500 font-mono">
          {new Date().toLocaleTimeString()}
        </div>
      </div>
    </motion.div>
  )
})

export default VideoCanvas
