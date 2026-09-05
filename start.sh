#!/usr/bin/env bash
# ai-qiuzhi 一键启动脚本
set -e
cd "$(dirname "$0")"

# 1. 安装后端依赖（首次）
if [ ! -d "backend/.venv" ]; then
  echo "==> 创建后端虚拟环境并安装依赖..."
  cd backend && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements.txt && cd ..
fi

# 2. 初始化数据库 + 导入知识库（首次，数据库文件不存在时）
if [ ! -f "backend/data/ai-qiuzhi.db" ]; then
  echo "==> 初始化数据库并导入个人知识库..."
  cd backend && .venv/bin/python -m scripts.import_wiki && cd ..
fi

# 3. 启动后端
echo "==> 启动后端 http://localhost:8000"
(cd backend && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACKEND_PID=$!

# 4. 安装前端依赖（首次）
if [ ! -d "frontend/node_modules" ]; then
  echo "==> 安装前端依赖..."
  cd frontend && npm install && cd ..
fi

# 5. 启动前端
echo "==> 启动前端 http://localhost:5173"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT

echo ""
echo "  ✨ ai-qiuzhi 已启动"
echo "  前端:   http://localhost:5173"
echo "  后端:   http://localhost:8000  (/docs 查看 API)"
echo ""
echo "  按 Ctrl+C 停止"

wait