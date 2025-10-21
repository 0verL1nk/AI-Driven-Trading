#!/bin/bash
# 查看AI原始响应的日志

echo "🔍 查看AI原始响应 (最近的日志)"
echo "======================================"

# 查找最新的日志文件
LATEST_LOG=$(ls -t logs/*.log 2>/dev/null | head -1)

if [ -z "$LATEST_LOG" ]; then
    echo "❌ 未找到日志文件"
    echo "请先运行交易机器人: python main.py"
    exit 1
fi

echo "📁 日志文件: $LATEST_LOG"
echo ""

# 查找AI响应部分
echo "🤖 AI原始响应:"
echo "======================================"
grep -A 100 "AI RAW RESPONSE" "$LATEST_LOG" | tail -200

echo ""
echo "======================================"
echo "💭 提取的Thinking:"
echo "======================================"
grep "Thinking extracted\|Thinking preview\|No <think>" "$LATEST_LOG" | tail -10

echo ""
echo "======================================"
echo "💡 提示:"
echo "如果显示 'No <think> or <reasoning> tags found'"
echo "说明AI没有输出thinking标签，需要修改prompt"

