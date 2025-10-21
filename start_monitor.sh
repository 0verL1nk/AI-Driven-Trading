#!/bin/bash

echo "========================================="
echo "  AI Trading Monitor - Startup Script"
echo "========================================="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python -m venv venv"
    exit 1
fi

# 启动后端API
echo "🚀 Starting Backend API Server..."
source venv/bin/activate
python web_monitor.py &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"
sleep 3

# 启动前端
echo ""
echo "🎨 Starting Frontend Next.js App..."
cd frontend

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo "   Installing dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "========================================="
echo "✅ Monitor System Started!"
echo "========================================="
echo ""
echo "📊 Dashboard: http://localhost:3000"
echo "🔌 API Docs:  http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# 等待用户中断
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

