#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "========================================="
echo "VLN System 后端服务启动"
echo "========================================="

# 检查依赖服务
echo "检查依赖服务..."

# 检查vLLM
echo -n "检查vLLM服务... "
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ 运行中"
else
    echo "✗ 未运行"
    echo ""
    echo "警告: vLLM服务未运行"
    echo "请在另一终端执行: bash scripts/start_vllm.sh"
    echo ""
    read -p "是否继续启动后端? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 初始化数据库
echo "初始化数据库..."
python scripts/init_db.py

# 启动FastAPI
echo ""
echo "========================================="
echo "启动FastAPI服务..."
echo "地址: http://localhost:8001"
echo "文档: http://localhost:8001/docs"
echo "========================================="
echo ""

cd backend
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --log-level info
