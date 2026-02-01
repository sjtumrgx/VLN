#!/bin/bash
set -e

cd "$(dirname "$0")/../frontend"

echo "========================================="
echo "VLN System 前端服务启动"
echo "========================================="

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "前端依赖未安装，正在安装..."
    npm install
fi

echo ""
echo "访问地址: http://localhost:5173"
echo "========================================="
echo ""

# 启动Vite开发服务器
exec npm run dev
