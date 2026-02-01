import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

export default function VideoCanvas({ wsClient, currentTask, stats }) {
  const canvasRef = useRef(null)
  const videoRef = useRef(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [frameCount, setFrameCount] = useState(0)
  const streamIntervalRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')

    // 监听导航结果
    const handleNavResult = (data) => {
      if (data.frame_with_trajectory) {
        const img = new Image()
        img.onload = () => {
          ctx.clearRect(0, 0, canvas.width, canvas.height)
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          setFrameCount(prev => prev + 1)
        }
        img.src = `data:image/jpeg;base64,${data.frame_with_trajectory}`
      }
    }

    wsClient.on('navigation_result', handleNavResult)

    return () => {
      wsClient.off('navigation_result', handleNavResult)
    }
  }, [wsClient])

  const startVideoStream = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      })

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        videoRef.current.play()
      }

      setIsStreaming(true)

      // 开始发送帧
      streamIntervalRef.current = setInterval(() => {
        if (canvasRef.current && videoRef.current && currentTask) {
          const tempCanvas = document.createElement('canvas')
          tempCanvas.width = 640
          tempCanvas.height = 480
          const tempCtx = tempCanvas.getContext('2d')
          tempCtx.drawImage(videoRef.current, 0, 0, 640, 480)

          tempCanvas.toBlob((blob) => {
            const reader = new FileReader()
            reader.onloadend = () => {
              const base64 = reader.result.split(',')[1]
              wsClient.sendVideoFrame(base64, currentTask.id, currentTask.instruction)
            }
            reader.readAsDataURL(blob)
          }, 'image/jpeg', 0.85)
        }
      }, 100) // 10 FPS
    } catch (err) {
      console.error('无法访问摄像头:', err)
      alert('无法访问摄像头，请检查权限设置')
    }
  }

  const stopVideoStream = () => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current)
      streamIntervalRef.current = null
    }

    if (videoRef.current && videoRef.current.srcObject) {
      const stream = videoRef.current.srcObject
      stream.getTracks().forEach(track => track.stop())
      videoRef.current.srcObject = null
    }

    setIsStreaming(false)
  }

  const loadTestVideo = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'video/*'
    input.onchange = (e) => {
      const file = e.target.files[0]
      if (file && videoRef.current) {
        const url = URL.createObjectURL(file)
        videoRef.current.src = url
        videoRef.current.play()
        setIsStreaming(true)

        // 视频播放时发送帧
        videoRef.current.ontimeupdate = () => {
          if (canvasRef.current && currentTask) {
            const tempCanvas = document.createElement('canvas')
            tempCanvas.width = 640
            tempCanvas.height = 480
            const tempCtx = tempCanvas.getContext('2d')
            tempCtx.drawImage(videoRef.current, 0, 0, 640, 480)

            tempCanvas.toBlob((blob) => {
              const reader = new FileReader()
              reader.onloadend = () => {
                const base64 = reader.result.split(',')[1]
                wsClient.sendVideoFrame(base64, currentTask.id, currentTask.instruction)
              }
              reader.readAsDataURL(blob)
            }, 'image/jpeg', 0.85)
          }
        }
      }
    }
    input.click()
  }

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
          width={640}
          height={480}
          className="w-full h-full object-contain"
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
}
