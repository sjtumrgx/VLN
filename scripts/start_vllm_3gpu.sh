#!/bin/bash
set -e

# 默认使用8B模型
HF_CACHE_PATH="${MODEL_PATH:-/data1/Qwen3VL/models--Qwen--Qwen3-VL-8B-Instruct}"

# 只使用GPU 0,1,3（跳过被系统占用的GPU 2）
export CUDA_VISIBLE_DEVICES=0,1,3

echo "========================================="
echo "vLLM 推理服务启动 (3-GPU模式)"
echo "========================================="

# 检查模型路径
if [ ! -d "$HF_CACHE_PATH" ]; then
    echo "错误: 模型路径不存在: $HF_CACHE_PATH"
    exit 1
fi

# 处理HF缓存目录结构
if [ -d "$HF_CACHE_PATH/snapshots" ]; then
    SNAPSHOT_DIR=$(ls -t "$HF_CACHE_PATH/snapshots" | head -1)
    MODEL_PATH="$HF_CACHE_PATH/snapshots/$SNAPSHOT_DIR"
    echo "检测到HuggingFace缓存目录结构"
else
    MODEL_PATH="$HF_CACHE_PATH"
fi

# 验证config.json
if [ ! -f "$MODEL_PATH/config.json" ]; then
    echo "错误: 找不到 config.json"
    exit 1
fi

echo ""
echo "模型路径: $MODEL_PATH"
echo "使用GPU: 0, 1, 3 (跳过GPU 2)"
echo "张量并行: 3 GPUs"
echo "显存利用率: 0.90"
echo "========================================="
echo ""

# 激活虚拟环境
source "$(dirname "$0")/../.venv/bin/activate"

echo "启动vLLM服务..."
echo ""

# 启动vLLM（3卡张量并行）
exec python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL_PATH" \
    --tensor-parallel-size 3 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 8192 \
    --host 0.0.0.0 \
    --port 8000 \
    --served-model-name qwen3-vl \
    --trust-remote-code \
    --disable-log-requests
