import { useState } from 'react'
import { motion } from 'framer-motion'

export default function ControlPanel({ onCreateTask, onStopTask, currentTask, velocity, confidence, connected }) {
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!instruction.trim() || loading || !connected) return

    setLoading(true)
    try {
      await onCreateTask(instruction.trim())
      setInstruction('')
    } catch (err) {
      console.error('提交失败:', err)
      alert('创建任务失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  const vPercent = Math.min((Math.abs(velocity.v) / 1.0) * 100, 100)
  const wPercent = Math.min((Math.abs(velocity.w) / 1.57) * 100, 100)

  return (
    <motion.div
      className="glass rounded-2xl p-6 space-y-6 corner-brackets relative overflow-hidden"
      initial={{ scale: 0.95 }}
      animate={{ scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Title */}
      <h2 className="text-sm font-display font-bold tracking-wider text-cyan-400 uppercase">
        控制面板
      </h2>

      {/* Instruction Input */}
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="relative">
          <label className="block text-xs font-mono text-gray-400 mb-2 uppercase tracking-wide">
            导航指令
          </label>
          <textarea
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="例如：去厨房拿水杯"
            rows={3}
            disabled={!connected}
            className="w-full px-4 py-3 bg-black/40 border-2 border-cyan-500/30 rounded-lg text-white font-mono text-sm focus:outline-none focus:border-cyan-400 focus:ring-4 focus:ring-cyan-400/20 transition-all resize-none disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button
            type="submit"
            disabled={!instruction.trim() || loading || !connected || currentTask}
            className="neon-button relative px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-display font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none transition-all uppercase tracking-wider text-sm"
          >
            {loading ? '发布中...' : currentTask ? '任务进行中' : '发布任务'}
          </button>

          <button
            type="button"
            onClick={() => onStopTask()}
            disabled={!currentTask}
            className="neon-button relative px-6 py-3 bg-gradient-to-r from-red-500 to-orange-600 text-white font-display font-bold rounded-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none transition-all uppercase tracking-wider text-sm"
          >
            停止任务
          </button>
        </div>
      </form>

      {/* Velocity Display */}
      <div className="space-y-4 pt-4 border-t border-cyan-500/20">
        <h3 className="text-xs font-mono text-gray-400 uppercase tracking-wide">速度指令</h3>

        {/* Linear Velocity */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">线速度 v</span>
            <span className="text-sm font-mono text-green-400 font-semibold">{velocity.v.toFixed(3)} m/s</span>
          </div>
          <div className="h-2 bg-black/40 rounded-full overflow-hidden border border-green-500/30">
            <motion.div
              className="h-full bg-gradient-to-r from-green-400 to-green-600 glow-green"
              initial={{ width: 0 }}
              animate={{ width: `${vPercent}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>

        {/* Angular Velocity */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">角速度 w</span>
            <span className="text-sm font-mono text-blue-400 font-semibold">{velocity.w.toFixed(3)} rad/s</span>
          </div>
          <div className="h-2 bg-black/40 rounded-full overflow-hidden border border-blue-500/30">
            <motion.div
              className="h-full bg-gradient-to-r from-blue-400 to-blue-600"
              initial={{ width: 0 }}
              animate={{ width: `${wPercent}%` }}
              transition={{ duration: 0.3 }}
              style={{
                boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)'
              }}
            />
          </div>
        </div>

        {/* Confidence */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs font-mono text-gray-400 uppercase">置信度</span>
          <div className="flex items-center gap-3">
            <div className="relative w-12 h-12">
              {/* Background circle */}
              <svg className="w-12 h-12 transform -rotate-90">
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke="rgba(148, 163, 184, 0.2)"
                  strokeWidth="4"
                  fill="none"
                />
                <motion.circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke={confidence > 0.7 ? '#10b981' : confidence > 0.4 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="4"
                  fill="none"
                  strokeLinecap="round"
                  initial={{ strokeDasharray: '0 126' }}
                  animate={{ strokeDasharray: `${confidence * 126} 126` }}
                  transition={{ duration: 0.5 }}
                  style={{
                    filter: `drop-shadow(0 0 6px ${confidence > 0.7 ? '#10b981' : confidence > 0.4 ? '#f59e0b' : '#ef4444'}80)`
                  }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-xs font-mono font-bold text-white">
                  {Math.round(confidence * 100)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Current Task Info */}
      {currentTask && (
        <motion.div
          className="p-4 bg-cyan-500/10 border border-cyan-500/30 rounded-lg"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="text-xs font-mono text-gray-400 mb-1">当前任务</div>
              <div className="text-sm font-mono text-white">{currentTask.instruction}</div>
            </div>
            <div className="flex-shrink-0 ml-3">
              <div className="px-2 py-1 bg-green-500/20 border border-green-500 rounded text-xs font-mono text-green-400">
                运行中
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
