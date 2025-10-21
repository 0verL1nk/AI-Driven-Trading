#!/usr/bin/env python3
"""
测试AI Thinking提取功能 - 简化版
"""
import re


def extract_thinking(response_text: str) -> str:
    """从LLM响应中提取thinking部分（复制自llm_interface.py）"""
    # 尝试提取<think>标签
    think_match = re.search(r'<think>(.*?)</think>', response_text, re.DOTALL)
    if think_match:
        return think_match.group(1).strip()
    
    # 尝试提取<reasoning>标签
    reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', response_text, re.DOTALL)
    if reasoning_match:
        return reasoning_match.group(1).strip()
    
    return ""


def test_thinking_extraction():
    """测试_extract_thinking方法"""
    
    # 测试用例1: 使用<think>标签
    response1 = """
<think>
这是我的思考过程：
1. BTC当前价格在110K附近
2. MACD显示下跌趋势
3. RSI在38，偏低但未超卖
4. 建议观望等待更好的入场点
</think>

{
  "BTC": {
    "coin": "BTC",
    "signal": "no_action",
    "leverage": 5,
    "confidence": 0.5
  }
}
"""
    
    # 测试用例2: 使用<reasoning>标签
    response2 = """
<reasoning>
市场分析：
- ETH价格从4027跌至3970，跌幅约1.4%
- RSI-7在15.4，严重超卖
- 可能出现反弹机会
- 建议小仓位做多
</reasoning>

{
  "ETH": {
    "coin": "ETH",
    "signal": "entry",
    "leverage": 8,
    "confidence": 0.65,
    "risk_usd": 100,
    "profit_target": 4100,
    "stop_loss": 3900,
    "invalidation_condition": "If price closes below 3850"
  }
}
"""
    
    # 测试用例3: 没有thinking标签
    response3 = """
{
  "BTC": {
    "coin": "BTC",
    "signal": "no_action",
    "leverage": 5,
    "confidence": 0.5
  }
}
"""
    
    print("=" * 100)
    print("🧪 测试AI Thinking提取功能")
    print("=" * 100)
    
    # 测试1
    print("\n📝 测试1: <think>标签")
    thinking1 = extract_thinking(response1)
    print(f"提取结果:\n{thinking1}")
    print(f"长度: {len(thinking1)} 字符")
    print(f"状态: {'✅ 成功' if thinking1 else '❌ 失败'}")
    
    # 测试2
    print("\n📝 测试2: <reasoning>标签")
    thinking2 = extract_thinking(response2)
    print(f"提取结果:\n{thinking2}")
    print(f"长度: {len(thinking2)} 字符")
    print(f"状态: {'✅ 成功' if thinking2 else '❌ 失败'}")
    
    # 测试3
    print("\n📝 测试3: 无标签")
    thinking3 = extract_thinking(response3)
    print(f"提取结果: '{thinking3}'")
    print(f"长度: {len(thinking3)} 字符")
    print(f"状态: {'✅ 正确（返回空字符串）' if thinking3 == '' else '❌ 应该返回空字符串'}")
    
    print("\n" + "=" * 100)
    print("💡 结论:")
    print("=" * 100)
    
    if thinking1 and thinking2 and thinking3 == '':
        print("✅ thinking提取功能正常！")
        print("\n📌 问题诊断:")
        print("1. ✅ 提取逻辑正确")
        print("2. ❓ LLM是否在响应中包含<think>或<reasoning>标签？")
        print("3. ❓ 需要检查实际的LLM响应内容")
    else:
        print("❌ thinking提取功能异常，需要修复！")
    
    print("=" * 100)
    
    # 显示如何让AI输出thinking
    print("\n📋 如何让AI输出thinking过程:")
    print("=" * 100)
    print("""
需要在prompt中添加以下指令：

方式1: 在prompt开头添加系统指令
─────────────────────────────────────
Before providing your JSON decision, you MUST think through your analysis 
step by step inside <think></think> tags.

<think>
1. Analyze current market conditions for each coin
2. Review technical indicators (MACD, RSI, EMA)
3. Assess risk/reward ratio
4. Make final decision with justification
</think>

After your thinking, output the JSON decision.


方式2: 中文版本
─────────────────────────────────────
在提供JSON决策之前，你必须在<think></think>标签中逐步思考你的分析过程：

<think>
1. 分析每个币种的当前市场状况
2. 审查技术指标（MACD, RSI, EMA）
3. 评估风险/收益比
4. 做出最终决策并说明理由
</think>

思考完成后，输出JSON决策。


方式3: 使用DeepSeek-R1等reasoning模型
─────────────────────────────────────
DeepSeek-R1会自动在<think>标签中输出推理过程，无需额外提示。
    """)
    print("=" * 100)
    
    # 检查数据库
    print("\n🔍 检查数据库中的thinking字段:")
    print("=" * 100)
    print("""
运行以下命令检查数据库：

sqlite3 trading_data.db "SELECT id, coin, decision, thinking FROM ai_decisions ORDER BY timestamp DESC LIMIT 5"

如果thinking字段为空，说明：
1. LLM响应中没有包含<think>或<reasoning>标签
2. 需要在prompt中添加上述指令
    """)
    print("=" * 100)


if __name__ == "__main__":
    test_thinking_extraction()

