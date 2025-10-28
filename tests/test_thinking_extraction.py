#!/usr/bin/env python3
"""
测试AI Thinking提取功能
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from ai.llm_interface import LLMInterface


def test_thinking_extraction():
    """测试_extract_thinking方法"""
    
    llm = LLMInterface()
    
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
    thinking1 = llm._extract_thinking(response1)
    print(f"提取结果: {repr(thinking1)}")
    print(f"长度: {len(thinking1)} 字符")
    print(f"状态: {'✅ 成功' if thinking1 else '❌ 失败'}")
    
    # 测试2
    print("\n📝 测试2: <reasoning>标签")
    thinking2 = llm._extract_thinking(response2)
    print(f"提取结果: {repr(thinking2)}")
    print(f"长度: {len(thinking2)} 字符")
    print(f"状态: {'✅ 成功' if thinking2 else '❌ 失败'}")
    
    # 测试3
    print("\n📝 测试3: 无标签")
    thinking3 = llm._extract_thinking(response3)
    print(f"提取结果: {repr(thinking3)}")
    print(f"长度: {len(thinking3)} 字符")
    print(f"状态: {'✅ 正确' if thinking3 == '' else '❌ 应该返回空字符串'}")
    
    print("\n" + "=" * 100)
    print("💡 结论:")
    print("=" * 100)
    
    if thinking1 and thinking2 and thinking3 == '':
        print("✅ thinking提取功能正常！")
        print("\n📌 下一步:")
        print("1. 检查LLM是否在响应中包含<think>或<reasoning>标签")
        print("2. 如果使用OpenAI/Anthropic，需要在prompt中要求AI包含thinking过程")
        print("3. 如果使用DeepSeek-R1等reasoning模型，它们会自动包含<think>标签")
    else:
        print("❌ thinking提取功能异常，需要修复！")
    
    print("=" * 100)
    
    # 显示如何在prompt中要求thinking
    print("\n📋 如何让AI输出thinking过程:")
    print("=" * 100)
    print("""
在prompt中添加以下指令：

Before providing your JSON decision, please think through your analysis step by step 
inside <think></think> tags:

<think>
1. Current market condition for each coin
2. Technical indicator analysis
3. Risk/reward assessment
4. Final decision rationale
</think>

Then output your JSON decision.

或中文版本：

在提供JSON决策之前，请在<think></think>标签中逐步思考您的分析：

<think>
1. 每个币种的当前市场状况
2. 技术指标分析
3. 风险/收益评估
4. 最终决策理由
</think>

然后输出您的JSON决策。
    """)
    print("=" * 100)


if __name__ == "__main__":
    test_thinking_extraction()

