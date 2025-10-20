#!/bin/bash

# AI Trading Bot启动脚本

echo "========================================="
echo "  AI驱动加密货币交易系统"
echo "  基于nof1.ai架构"
echo "========================================="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 未找到虚拟环境。"
    echo "请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查配置
echo "🔍 检查配置..."
if [ ! -f ".env" ]; then
    echo "❌ 未找到.env文件"
    echo "请先复制: cp .env.example .env"
    echo "然后编辑.env填入API密钥"
    exit 1
fi

# 运行配置检查
python scripts/check_config.py
if [ $? -ne 0 ]; then
    echo ""
    echo "❌ 配置检查失败，请修复后重试"
    exit 1
fi

# 运行系统测试（可选）
read -p "是否运行系统测试？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧪 运行系统测试..."
    python test_system.py
    if [ $? -ne 0 ]; then
        echo "❌ 系统测试失败"
        exit 1
    fi
fi

# 确认启动
echo ""
echo "准备启动交易系统..."
echo ""
echo "⚠️  重要提醒："
echo "  1. 确保已设置ENABLE_PAPER_TRADING=true（模拟交易）"
echo "  2. 系统将每2.6分钟调用一次AI API"
echo "  3. 请确保有足够的API余额"
echo "  4. 可以随时按Ctrl+C停止"
echo ""

read -p "确认启动？(y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 创建日志目录
mkdir -p logs

# 启动系统
echo ""
echo "🚀 启动交易系统..."
echo "日志文件: logs/trading.log"
echo "按Ctrl+C停止"
echo ""
echo "========================================="
echo ""

python main.py

