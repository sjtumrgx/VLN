import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const STATUS_CONFIG = {
  pending: { label: '等待中', color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500' },
  running: { label: '运行中', color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500' },
  stopped: { label: '已停止', color: 'text-gray-300', bg: 'bg-gray-500/20', border: 'border-gray-500' },
  completed: { label: '已完成', color: 'text-blue-400', bg: 'bg-blue-500/20', border: 'border-blue-500' },
  failed: { label: '失败', color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500' },
}

export default function TaskHistory({ tasks, currentTaskId, onStopTask }) {
  const [expanded, setExpanded] = useState(null)
  const [collapsed, setCollapsed] = useState(false)

  const displayTasks = tasks.slice(0, 5)

  return (
    <motion.div
      className="glass rounded-2xl h-full flex flex-col corner-brackets relative overflow-hidden"
      initial={{ scale: 0.95 }}
      animate={{ scale: 1 }}
      transition={{ duration: 0.5 }}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-cyan-500/20">
        <h2 className="text-sm font-display font-bold tracking-wider text-cyan-400 uppercase">
          任务历史
        </h2>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-xs font-mono text-gray-400 hover:text-cyan-400 transition-colors"
        >
          {collapsed ? '展开' : '收起'}
        </button>
      </div>

      {/* Task List */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            className="flex-1 overflow-y-auto p-4 space-y-3"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            {displayTasks.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <p className="text-sm text-gray-500 font-mono">暂无任务历史</p>
              </div>
            ) : (
              displayTasks.map((task, index) => (
                <TaskItem
                  key={task.id}
                  task={task}
                  isExpanded={expanded === task.id}
                  isCurrent={task.id === currentTaskId}
                  onToggle={() => setExpanded(expanded === task.id ? null : task.id)}
                  onStopTask={onStopTask}
                  index={index}
                />
              ))
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function TaskItem({ task, isExpanded, isCurrent, onToggle, onStopTask, index }) {
  const config = STATUS_CONFIG[task.status] || STATUS_CONFIG.pending
  const canStop = task.status === 'pending' || task.status === 'running'

  return (
    <motion.div
      className={`relative cursor-pointer transition-all ${
        isCurrent ? 'ring-2 ring-cyan-400/50' : ''
      }`}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      onClick={onToggle}
    >
      <div className="bg-black/30 border border-cyan-500/20 rounded-lg p-3 hover:border-cyan-500/40 hover:bg-black/40 transition-all">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-mono text-white truncate">
              {task.instruction}
            </p>
            <p className="text-xs text-gray-500 font-mono mt-1">
              {new Date(task.created_at).toLocaleString('zh-CN')}
            </p>
          </div>
          <div className={`px-2 py-0.5 ${config.bg} border ${config.border} rounded text-xs font-mono ${config.color} flex-shrink-0`}>
            {config.label}
          </div>
          {canStop && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onStopTask?.(task.id)
              }}
              className="px-2 py-0.5 bg-red-500/20 border border-red-500 rounded text-xs font-mono text-red-400 hover:bg-red-500/30 transition-all flex-shrink-0"
            >
              停止
            </button>
          )}
        </div>

        {/* Expanded Details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              className="mt-3 pt-3 border-t border-cyan-500/10 space-y-2"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
            >
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div>
                  <span className="text-gray-500">ID:</span>
                  <span className="ml-2 text-cyan-400">{task.id.slice(0, 8)}</span>
                </div>
                <div>
                  <span className="text-gray-500">状态:</span>
                  <span className={`ml-2 ${config.color}`}>{config.label}</span>
                </div>
              </div>
              {task.memory_summary && (
                <div className="text-xs font-mono">
                  <span className="text-gray-500">记忆:</span>
                  <p className="mt-1 text-gray-400">{task.memory_summary}</p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Current Task Indicator */}
        {isCurrent && (
          <div className="absolute -left-1 top-1/2 -translate-y-1/2 w-1 h-8 bg-cyan-400 rounded-r animate-pulse-glow" />
        )}
      </div>
    </motion.div>
  )
}
