import { motion } from 'framer-motion'

export default function Header({ connected, modelStatus, selectedModel, onModelChange }) {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 z-50">
      <div className="absolute inset-0 glass border-b border-cyan-500/20" />

      <div className="relative h-full max-w-[1920px] mx-auto px-6 flex items-center justify-between">
        {/* Logo & Title */}
        <motion.div
          className="flex items-center gap-4"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="w-10 h-10 relative">
            <div className="absolute inset-0 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-lg rotate-45" />
            <div className="absolute inset-0.5 bg-cyber-bg rounded-lg rotate-45" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-cyan-400 text-xl font-bold font-display">V</span>
            </div>
          </div>
          <div>
            <h1 className="text-xl font-display font-bold tracking-wider bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">
              VLN NAVIGATION
            </h1>
            <p className="text-xs text-gray-400 font-mono">SYSTEM v0.1.0</p>
          </div>
        </motion.div>

        {/* Model Selector */}
        <motion.div
          className="flex items-center gap-3"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <span className="text-xs text-gray-400 font-mono uppercase tracking-wide">Model:</span>
          <select
            value={selectedModel}
            onChange={(e) => onModelChange(e.target.value)}
            className="bg-slate-800/60 border border-cyan-500/30 rounded-lg px-4 py-2 text-sm font-mono text-cyan-400 focus:outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-400/20 transition-all cursor-pointer"
          >
            <option value="qwen3-vl-8b">Qwen3-VL-8B</option>
            <option value="qwen3-vl-30b">Qwen3-VL-30B</option>
          </select>
        </motion.div>

        {/* Status Indicators */}
        <motion.div
          className="flex items-center gap-6"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {/* WebSocket Status */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className={`w-2.5 h-2.5 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
              {connected && (
                <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-green-400 animate-ping" />
              )}
            </div>
            <span className="text-xs font-mono text-gray-400">
              WS: {connected ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>

          {/* vLLM Status */}
          <div className="flex items-center gap-2">
            <div className="relative">
              <div className={`w-2.5 h-2.5 rounded-full ${
                modelStatus === 'loaded' ? 'bg-green-400' :
                modelStatus === 'loading' ? 'bg-yellow-400' : 'bg-red-400'
              }`} />
              {modelStatus === 'loaded' && (
                <div className="absolute inset-0 w-2.5 h-2.5 rounded-full bg-green-400 animate-ping" />
              )}
            </div>
            <span className="text-xs font-mono text-gray-400">
              vLLM: {modelStatus.toUpperCase()}
            </span>
          </div>
        </motion.div>
      </div>
    </header>
  )
}
