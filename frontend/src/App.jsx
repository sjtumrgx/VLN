import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import Header from './components/Header'
import VideoCanvas from './components/VideoCanvas'
import ControlPanel from './components/ControlPanel'
import TaskHistory from './components/TaskHistory'
import WebSocketClient from './services/websocket'
import { api } from './services/api'

function App() {
  const [wsClient] = useState(() => new WebSocketClient('ws://localhost:8001/ws/video'))
  const [connected, setConnected] = useState(false)
  const [currentTask, setCurrentTask] = useState(null)
  const [tasks, setTasks] = useState([])
  const [velocity, setVelocity] = useState({ v: 0, w: 0 })
  const [confidence, setConfidence] = useState(0)
  const [modelStatus, setModelStatus] = useState('unknown')
  const [selectedModel, setSelectedModel] = useState('qwen3-vl-8b')
  const [videoStats, setVideoStats] = useState({ fps: 0, latency: 0 })

  useEffect(() => {
    // 连接WebSocket
    wsClient.connect()

    wsClient.on('connected', () => {
      console.log('已连接到服务器')
      setConnected(true)
    })

    wsClient.on('disconnected', () => {
      console.log('与服务器断开连接')
      setConnected(false)
    })

    wsClient.on('navigation_result', (data) => {
      setVelocity({ v: data.v, w: data.w })
      setConfidence(data.confidence || 0)
      setVideoStats({
        fps: data.fps || 0,
        latency: Math.round(data.latency) || 0
      })
    })

    // 定期心跳
    const heartbeat = setInterval(() => {
      if (wsClient.isConnected) {
        wsClient.ping()
      }
    }, 30000)

    // 获取模型状态
    const checkModel = async () => {
      try {
        const status = await api.getModelStatus()
        setModelStatus(status.status)
      } catch (err) {
        console.error('获取模型状态失败:', err)
        setModelStatus('error')
      }
    }
    checkModel()
    const modelCheck = setInterval(checkModel, 10000)

    // 获取任务列表
    const fetchTasks = async () => {
      try {
        const taskList = await api.listTasks(10)
        setTasks(taskList)
      } catch (err) {
        console.error('获取任务列表失败:', err)
      }
    }
    fetchTasks()

    return () => {
      wsClient.disconnect()
      clearInterval(heartbeat)
      clearInterval(modelCheck)
    }
  }, [wsClient])

  const handleCreateTask = async (instruction) => {
    try {
      const task = await api.createTask(instruction)
      setCurrentTask(task)
      setTasks(prev => [task, ...prev])

      // 绑定任务到WebSocket
      wsClient.bindTask(task.id)

      return task
    } catch (err) {
      console.error('创建任务失败:', err)
      throw err
    }
  }

  const handleStopTask = async () => {
    if (currentTask) {
      try {
        await api.updateTask(currentTask.id, { status: 'completed' })
        setCurrentTask(null)
        setVelocity({ v: 0, w: 0 })
      } catch (err) {
        console.error('停止任务失败:', err)
      }
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-cyber-bg to-cyber-bg-light text-gray-100">
      {/* Grid background */}
      <div className="fixed inset-0 grid-bg opacity-30 pointer-events-none" />

      {/* Header */}
      <Header
        connected={connected}
        modelStatus={modelStatus}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
      />

      {/* Main Content */}
      <main className="pt-16 px-6 pb-6 relative z-10">
        <div className="max-w-[1920px] mx-auto h-[calc(100vh-88px)] flex gap-6">
          {/* Left Panel - Video */}
          <motion.div
            className="flex-[65] flex flex-col"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <VideoCanvas
              wsClient={wsClient}
              currentTask={currentTask}
              stats={videoStats}
            />
          </motion.div>

          {/* Right Panel - Controls & History */}
          <motion.div
            className="flex-[35] flex flex-col gap-6 overflow-hidden"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            {/* Control Panel */}
            <div className="flex-shrink-0">
              <ControlPanel
                onCreateTask={handleCreateTask}
                onStopTask={handleStopTask}
                currentTask={currentTask}
                velocity={velocity}
                confidence={confidence}
                connected={connected}
              />
            </div>

            {/* Task History */}
            <div className="flex-1 overflow-hidden">
              <TaskHistory tasks={tasks} currentTaskId={currentTask?.id} />
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  )
}

export default App
