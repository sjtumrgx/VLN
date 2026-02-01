#!/bin/bash
set -e

# 默认使用8B模型的HF缓存目录
HF_CACHE_PATH="${MODEL_PATH:-/data1/Qwen3VL/models--Qwen--Qwen3-VL-8B-Instruct}"
# 可选30B模型：export MODEL_PATH=/data1/Qwen3VL/models--Qwen--Qwen3-VL-30B-A3B-Instruct

# 显存利用率（降低以避免GPU 2的系统占用）
GPU_MEM_UTIL="${GPU_MEMORY_UTILIZATION:-0.80}"

echo "========================================="
echo "vLLM 推理服务启动"
echo "========================================="

# 检查模型路径
if [ ! -d "$HF_CACHE_PATH" ]; then
    echo "错误: 模型路径不存在: $HF_CACHE_PATH"
    echo "请设置环境变量 MODEL_PATH 指向正确的模型目录"
    exit 1
fi

# 处理HuggingFace缓存目录结构
if [ -d "$HF_CACHE_PATH/snapshots" ]; then
    SNAPSHOT_DIR=$(ls -t "$HF_CACHE_PATH/snapshots" | head -1)
    MODEL_PATH="$HF_CACHE_PATH/snapshots/$SNAPSHOT_DIR"
    echo "检测到HuggingFace缓存目录结构"
    echo "实际模型路径: $MODEL_PATH"
else
    MODEL_PATH="$HF_CACHE_PATH"
fi

# 验证config.json存在
if [ ! -f "$MODEL_PATH/config.json" ]; then
    echo "错误: 找不到 config.json 文件"
    echo "路径: $MODEL_PATH"
    echo ""
    echo "请确保指定的路径包含完整的模型文件"
    exit 1
fi

echo ""
echo "模型路径: $MODEL_PATH"
echo "监听地址: 0.0.0.0:8000"
echo "张量并行: 4 GPUs"
echo "显存利用率: ${GPU_MEM_UTIL} (调整以适应系统占用)"
echo "========================================="

# 检查GPU显存使用情况
echo ""
echo "当前GPU显存状态："
nvidia-smi --query-gpu=index,name,memory.used,memory.free --format=csv,noheader,nounits | \
    awk '{printf "  GPU %s: 已用 %sMiB, 可用 %sMiB\n", $1, $3, $4}'
echo ""

# 激活虚拟环境
source "$(dirname "$0")/../.venv/bin/activate"

# 检查vLLM是否安装
python -c "import vllm" 2>/dev/null || {
    echo ""
    echo "警告: vLLM未安装，正在安装..."
    uv pip install "vllm>=0.6.0" "torch>=2.1.0" "transformers>=4.37.0"
}

echo ""
echo "启动vLLM服务..."
echo "提示: 首次启动需要1-2分钟加载模型，请耐心等待"
echo ""

# 启动vLLM服务
exec python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --tensor-parallel-size 4 \
    --gpu-memory-utilization "$GPU_MEM_UTIL" \
    --max-model-len 6144 \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name qwen3-vl \
    --trust-remote-code \
    --disable-log-requests
