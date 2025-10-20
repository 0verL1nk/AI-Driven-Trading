# 使用推理模型（Reasoning Models）

## 🧠 什么是推理模型？

推理模型（如OpenAI的o1系列）是专门设计用于复杂推理任务的大语言模型。它们的特点是：

- **显式思考过程**：模型会先"思考"再给出答案
- **更长的推理时间**：通常比GPT-4慢，但更准确
- **思维链输出**：使用`<think></think>`标签包裹思考过程

## 📊 推理模型 vs 标准模型

### OpenAI GPT-4 (标准模型)

```json
{
  "BTC": {
    "trade_signal_args": {
      "signal": "entry",
      "leverage": 10
    }
  }
}
```

### OpenAI o1 (推理模型)

```
<think>
Let me analyze the BTC market data:
1. Current price is 110909.5, below EMA20 (111159.342)
2. MACD is negative (-33.349), showing bearish momentum
3. RSI is 38.262, not oversold yet
4. However, 4H timeframe shows MACD turning positive
5. Funding rate is slightly negative, suggesting...

Based on this analysis, I should wait for a better entry point.
</think>

{
  "BTC": {
    "trade_signal_args": {
      "signal": "no_action"
    }
  }
}
```

## 🔧 在本系统中使用推理模型

### 1. 配置OpenAI o1

编辑 `config/trading_config.yaml`:

```yaml
ai:
  provider: "openai"
  model: "o1-preview"  # 或 "o1-mini"
  temperature: 1.0     # o1模型固定为1.0
  max_tokens: 10000    # o1需要更多tokens
```

### 2. 系统自动处理

本系统已内置对`<think></think>`标签的处理：

```python
# src/ai/llm_interface.py
def _parse_response(self, response_text: str) -> Dict:
    # 自动移除推理过程
    if "<think>" in response_text and "</think>" in response_text:
        response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
    
    # 解析JSON
    decision = json.loads(response_text)
    return decision
```

### 3. 成本考虑

推理模型成本**显著高于**标准模型：

| 模型 | 输入价格 | 输出价格 | 每次决策估算 |
|------|---------|---------|------------|
| GPT-4 Turbo | $0.01/1K | $0.03/1K | ~$0.10 |
| o1-preview | $0.015/1K | $0.06/1K | ~$0.50-1.00 |
| o1-mini | $0.003/1K | $0.012/1K | ~$0.10-0.20 |

**每天成本估算**（每2.6分钟决策，~550次/天）：
- GPT-4 Turbo: ~$55/天
- o1-preview: ~$275-550/天 ⚠️
- o1-mini: ~$55-110/天

## 💡 何时使用推理模型？

### 适合场景

✅ **复杂市场条件**
- 多个相互矛盾的信号
- 需要深度分析的情况
- 市场结构复杂时

✅ **关键决策点**
- 大仓位开仓/平仓
- 市场转折点判断
- 高风险情况

✅ **策略研究**
- 回测和分析
- 理解AI决策逻辑
- 优化交易策略

### 不适合场景

❌ **高频交易**
- 成本过高
- 响应时间慢

❌ **简单信号**
- 明确的技术形态
- 标准模型足够

❌ **资金有限**
- 成本不可承受
- ROI不划算

## 🎯 推荐使用策略

### 策略1: 混合模式

```python
# 伪代码
def decide(market_data):
    # 使用GPT-4做日常决策
    decision = gpt4.decide(market_data)
    
    # 在关键时刻使用o1验证
    if is_critical_moment(market_data):
        o1_decision = o1.decide(market_data)
        
        # 如果两者一致，执行
        if decision == o1_decision:
            return decision
        else:
            # 不一致时保守处理
            return "no_action"
    
    return decision
```

### 策略2: 降低频率

```yaml
# 使用o1，但降低决策频率
ai:
  model: "o1-mini"
  decision_interval_minutes: 15  # 从2.6分钟改为15分钟
```

每天决策次数：96次
每天成本：~$10-20（可接受）

### 策略3: 仅用于验证

```python
# 每天运行一次o1进行策略审查
daily_review = o1.review_strategy(
    recent_trades,
    current_positions,
    market_conditions
)
```

## 📝 思维链日志

推理模型的思考过程非常有价值，建议保存：

```python
# src/ai/llm_interface.py (增强版)
def _parse_response(self, response_text: str) -> Dict:
    # 提取思维链
    thinking = ""
    if "<think>" in response_text:
        think_start = response_text.find("<think>") + 7
        think_end = response_text.find("</think>")
        thinking = response_text[think_start:think_end].strip()
        
        # 保存到日志
        logger.info(f"AI Reasoning:\n{thinking}")
        
        # 保存到文件（可选）
        with open('logs/reasoning.log', 'a') as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(thinking)
            f.write("\n")
    
    # 继续解析JSON...
```

## 🔍 调试推理模型

### 查看完整响应

```python
# 临时启用调试模式
import logging
logging.getLogger('src.ai.llm_interface').setLevel(logging.DEBUG)

# 运行系统，查看完整响应
```

### 测试推理质量

```python
# scripts/test_reasoning.py
from src.ai.llm_interface import TradingLLM
from src.ai.prompt_builder import PromptBuilder

# 对比GPT-4和o1的决策
gpt4 = TradingLLM(primary_provider="openai", model="gpt-4-turbo-preview")
o1 = TradingLLM(primary_provider="openai", model="o1-mini")

prompt = builder.build_trading_prompt(...)

gpt4_decision = await gpt4.decide(prompt)
o1_decision = await o1.decide(prompt)

print("GPT-4:", gpt4_decision)
print("o1:", o1_decision)
print("Agreement:", gpt4_decision == o1_decision)
```

## ⚠️ 注意事项

### 1. Token限制

推理模型有更严格的token限制：
- o1-preview: 128K输入，32K输出
- o1-mini: 128K输入，64K输出

本系统的Prompt通常~5-10K tokens，在限制内。

### 2. Temperature固定

推理模型的temperature参数**固定为1.0**，不能调整。

### 3. 响应时间

推理模型响应时间可能达到**30-60秒**，比GPT-4慢10倍。

### 4. 系统Prompt限制

某些推理模型可能不支持system prompt，需要将指令放入user prompt中。

## 🎓 最佳实践总结

1. **先用GPT-4测试**
   - 验证系统正常工作
   - 理解决策模式
   - 评估基准表现

2. **选择性使用o1**
   - 关键决策点
   - 复杂市场条件
   - 策略验证

3. **降低频率降成本**
   - 从2.6分钟改为10-15分钟
   - 仅在特定时段使用
   - 与标准模型混合

4. **保存思维链**
   - 学习AI的决策逻辑
   - 优化Prompt
   - 改进策略

5. **监控成本**
   - 设置预算警报
   - 定期检查API usage
   - 评估ROI

---

**推理模型是强大的工具，但要明智使用。在大多数情况下，GPT-4 Turbo已经足够好且成本更低。🚀**

