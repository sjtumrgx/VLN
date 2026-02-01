#!/bin/bash
# 一键启动所有服务

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "========================================"
echo "VLN System - 一键启动脚本"
echo "========================================"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查依赖
echo "检查依赖..."

# 检查Python虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Python虚拟环境未找到${NC}"
    echo "  请先运行: uv venv && uv pip install -e \".[dev]\""
    exit 1
fi
echo -e "${GREEN}✓ Python虚拟环境${NC}"

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}⚠ 前端依赖未安装，正在安装...${NC}"
    cd frontend
    npm install
    cd ..
fi
echo -e "${GREEN}✓ 前端依赖${NC}"

# 检查vLLM（可选）
echo ""
echo "检查vLLM服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ vLLM服务已运行${NC}"
else
    echo -e "${YELLOW}⚠ vLLM服务未运行${NC}"
    echo "  如需完整功能，请在另一终端执行:"
    echo "  bash scripts/start_vllm.sh"
    echo ""
fi

# 初始化数据库
echo "初始化数据库..."
source .venv/bin/activate
python scripts/init_db.py
echo ""

# 启动服务
echo "========================================"
echo "启动服务..."
echo "========================================"
echo ""

# 使用tmux或screen启动多个服务（如果可用）
if command -v tmux &> /dev/null; then
    echo "使用tmux启动服务..."

    # 创建新的tmux会话
    tmux new-session -d -s vln "bash scripts/start_backend.sh"
    tmux split-window -h -t vln "cd frontend && npm run dev"

    echo -e "${GREEN}✓ 服务已在tmux会话'vln'中启动${NC}"
    echo ""
    echo "查看服务: tmux attach -t vln"
    echo "分离会话: Ctrl+B 然后按 D"
    echo "关闭服务: tmux kill-session -t vln"
    echo ""

    # 等待服务启动
    sleep 3

    echo "========================================"
    echo "服务地址:"
    echo "========================================"
    echo "前端: http://localhost:5173"
    echo "后端: http://localhost:8001"
    echo "API文档: http://localhost:8001/docs"
    echo ""

    # 自动打开浏览器（可选）
    if command -v xdg-open &> /dev/null; then
        echo "正在打开浏览器..."
        sleep 2
        xdg-open http://localhost:5173 2>/dev/null &
    fi

else
    echo -e "${YELLOW}tmux未安装，请手动在不同终端启动：${NC}"
    echo ""
    echo "终端1: bash scripts/start_backend.sh"
    echo "终端2: cd frontend && npm run dev"
    echo ""
fi
