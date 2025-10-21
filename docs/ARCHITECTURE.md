# 系统架构设计文档

## 🏗️ 整体架构

基于对 nof1.ai 的深度分析，本系统采用四层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                       Trading Bot                            │
│                    (Main Orchestrator)                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐   ┌──────────────┐
│ Data Layer   │  │  AI Layer    │   │ Execution    │
│              │  │              │   │ Layer        │
└──────────────┘  └──────────────┘   └──────────────┘
        │                 │                   │
        └─────────────────┴───────────────────┘
                          │
                ┌─────────┴─────────┐
                │   Risk Manager    │
                └───────────────────┘
```

## 📊 数据层 (Data Layer)

### 职责
收集、处理和格式化市场数据供AI决策使用。

### 核心组件

#### 1. ExchangeClient (`src/data/exchange_client.py`)
- **功能**：与交易所API交互
- **实现**：基于CCXT统一接口
- **支持操作**：
  - 实时K线数据获取（1m, 3m, 15m, 4h）
  - 资金费率和持仓量查询
  - 订单执行（市价、限价、止损、止盈）
  - 账户余额和持仓查询
  - 杠杆设置

```python
# 使用示例
client = ExchangeClient()
await client.load_markets()
ohlcv = await client.fetch_ohlcv('BTC/USDT:USDT', '3m', limit=100)
```

#### 2. IndicatorEngine (`src/data/indicator_engine.py`)
- **功能**：计算技术指标
- **实现**：TA-Lib + pandas-ta
- **支持指标**：
  - 趋势：EMA(20, 50), MACD(12, 26, 9)
  - 动量：RSI(7, 14)
  - 波动：ATR(14), Bollinger Bands
  - 成交量分析

```python
# 核心算法
df = indicator_engine.add_all_indicators(raw_ohlcv)
# 新增列：ema_20, ema_50, macd, rsi_7, rsi_14, atr_14, bb_upper, bb_lower
```

#### 3. 数据流程

```
交易所API → OHLCV数据 → 技术指标计算 → 格式化为Prompt
     ↓           ↓             ↓                ↓
  资金费率    持仓量      信号强度         nof1.ai格式
```

## 🤖 AI决策层 (AI Layer)

### 职责
基于LLM进行市场分析和交易决策。

### 核心组件

#### 1. PromptBuilder (`src/ai/prompt_builder.py`)
- **功能**：构建精确匹配 nof1.ai 格式的Prompt
- **关键特性**：
  - 完全复刻 nof1.ai 的Prompt结构
  - 包含最近10根3分钟K线序列
  - 包含4小时长周期趋势
  - 账户状态和持仓信息

```python
# Prompt结构（匹配UserPrompt.md）
"""
It has been {minutes} minutes since you started trading...

CURRENT MARKET STATE FOR ALL COINS
ALL BTC DATA
current_price = 110909.5, current_ema20 = 111159.342, ...
Mid prices: [111297.0, 111249.5, ...]
EMA indicators (20‑period): [111214.482, 111217.103, ...]
...

HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): 29.97%
Available Cash: 4927.64
...
"""
```

#### 2. TradingLLM (`src/ai/llm_interface.py`)
- **功能**：LLM调用和响应处理
- **支持提供商**：
  - OpenAI (GPT-4)
  - Anthropic (Claude)
  - 本地LLM (Ollama/vLLM)
- **关键特性**：
  - 自动降级（主Provider失败时切换到备用）
  - 重试机制（最多3次）
  - JSON格式强制输出
  - 错误处理和日志记录

```python
# 使用示例
llm = TradingLLM(primary_provider="openai", model="gpt-4-turbo-preview")
decisions = await llm.decide(prompt, temperature=0.3)
```

#### 3. DecisionValidator (`src/ai/decision_validator.py`)
- **功能**：验证AI决策的合理性和安全性
- **验证规则**：
  - 杠杆范围：5-15x
  - 置信度：0.5-1.0
  - 风险限制：单笔 ≤ 2% 账户资金
  - 风险回报比：≥ 1.5:1
  - 止损/止盈价格合理性

```python
# 验证逻辑
is_valid, error = validator.validate_decision(
    coin='BTC',
    decision=ai_output,
    current_price=110000,
    account_value=10000
)
```

### AI决策流程

```
市场数据 → Prompt构建 → LLM推理 → JSON解析 → 决策验证
    ↓          ↓           ↓          ↓          ↓
 6种币    nof1.ai格式   GPT-4分析  结构化输出  风控检查
```

## ⚙️ 执行层 (Execution Layer)

### 职责
执行交易决策并管理仓位。

### 核心组件

#### 1. OrderManager (`src/execution/order_manager.py`)
- **功能**：订单执行和管理
- **核心操作**：
  ```python
  async def execute_entry():
      # 1. 设置杠杆
      await exchange.set_leverage(symbol, leverage)
      
      # 2. 市价开仓
      entry_order = await exchange.create_market_order(...)
      
      # 3. 设置止损
      sl_order = await exchange.create_stop_loss_order(...)
      
      # 4. 设置止盈
      tp_order = await exchange.create_take_profit_order(...)
  ```

- **失效条件检查**：
  ```python
  # 示例：'If the price closes below 3800 on a 3-minute candle'
  if current_price < threshold:
      await execute_close(coin, symbol, position)
  ```

#### 2. PortfolioManager (`src/execution/portfolio_manager.py`)
- **功能**：组合管理和绩效跟踪
- **核心指标**：
  - 总收益率
  - 夏普比率
  - 最大回撤
  - 胜率
  - 盈亏比

```python
# 夏普比率计算（年化）
returns = np.diff(equity_curve) / equity_curve[:-1]
sharpe = np.mean(returns) / np.std(returns) * sqrt(annualization_factor)
```

#### 3. PaperTradingEngine (`src/execution/paper_trading.py`)
- **功能**：模拟交易引擎
- **模拟要素**：
  - 滑点：0.1%
  - 手续费：Maker 0.02%, Taker 0.04%
  - 爆仓价格计算
  - 保证金管理

## 🔄 主循环逻辑

### TradingBot (`src/trading_bot.py`)

```python
while running:
    iteration += 1
    
    # Step 1: 收集市场数据
    market_data = await collect_market_data()
    # - 6种币的3分钟K线（最近100根）
    # - 6种币的4小时K线（最近100根）
    # - 资金费率、持仓量
    
    # Step 2: 获取账户状态
    balance = await exchange.fetch_balance()
    positions = await exchange.fetch_positions()
    account_state = portfolio.calculate_account_state(balance, positions)
    
    # Step 3: 检查失效条件
    to_invalidate = await check_invalidation_conditions(positions)
    for coin in to_invalidate:
        await order_manager.execute_close(coin)
    
    # Step 4: 构建Prompt
    prompt = prompt_builder.build_trading_prompt(
        market_data, account_state, positions
    )
    
    # Step 5: AI决策
    decisions = await llm.decide(prompt)
    
    # Step 6: 验证决策
    validated = validator.validate_all_decisions(decisions)
    
    # Step 7: 执行交易
    await execute_decisions(validated)
    
    # Step 8: 等待下次迭代（2.6分钟）
    await asyncio.sleep(decision_interval)
```

## 🛡️ 风险管理

### 多层风控机制

#### 1. 事前控制（Prompt层面）
```yaml
# 嵌入Prompt的风控规则
RISK MANAGEMENT RULES:
1. Maximum risk per trade: 2% of total account value
2. Each trade MUST have stop loss and take profit
3. Leverage: 5-15x based on confidence
4. Minimum risk/reward ratio: 1.5:1
```

#### 2. 决策验证（Validator层面）
```python
# DecisionValidator检查项
- 杠杆是否在5-15x范围内
- 单笔风险是否 <= 2% 账户
- 止损/止盈是否设置
- 风险回报比是否 >= 1.5
- 价格是否合理（止损不能在当前价上方）
```

#### 3. 执行保护（OrderManager层面）
```python
# 执行层检查
- 失效条件自动平仓
- 止损/止盈自动设置
- 持仓监控
```

#### 4. 账户保护（Portfolio层面）
```python
# config/risk_params.yaml
drawdown_protection:
  max_daily_drawdown_percent: 10.0  # 日内回撤>10%停止交易
  max_total_drawdown_percent: 25.0  # 总回撤>25%紧急关闭
  cooldown_period_minutes: 60
```

## 📈 数据流图

```
┌─────────────┐
│   Binance   │
│  (Exchange) │
└──────┬──────┘
       │ WebSocket/REST
       ▼
┌─────────────────┐
│ ExchangeClient  │ ← 3min K线, 4h K线, 资金费率
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ IndicatorEngine │ ← 计算EMA, MACD, RSI, ATR
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ PromptBuilder   │ ← 格式化为nof1.ai格式
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   TradingLLM    │ ← GPT-4 / Claude分析
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│DecisionValidator│ ← 风控检查
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  OrderManager   │ ← 执行交易
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│PortfolioManager │ ← 记录绩效
└─────────────────┘
```

## 🔧 配置系统

### 配置文件层次

```
config/
├── trading_config.yaml  # 交易配置
│   ├── exchange        # 交易所设置
│   ├── trading_pairs   # 交易对
│   ├── ai              # AI模型配置
│   └── paper_trading   # 模拟交易
│
└── risk_params.yaml    # 风控参数
    ├── position_sizing  # 仓位管理
    ├── leverage        # 杠杆设置
    ├── exit_strategy   # 止损止盈
    ├── diversification # 分散化
    └── drawdown_protection # 回撤保护
```

### 环境变量 (.env)
```
BINANCE_API_KEY         # 交易所密钥
OPENAI_API_KEY          # AI模型密钥
ENABLE_PAPER_TRADING    # 模拟/实盘切换
```

## 📊 性能优化

### 异步并发
```python
# 并行获取多个币种数据
tasks = [
    exchange.fetch_ohlcv(pair, '3m')
    for pair in trading_pairs
]
results = await asyncio.gather(*tasks)
```

### 缓存策略
```python
# Redis缓存市场数据（减少API调用）
if cached := await redis.get(f"ohlcv:{symbol}:{timeframe}"):
    return cached
else:
    data = await exchange.fetch_ohlcv(...)
    await redis.setex(f"ohlcv:{symbol}:{timeframe}", 60, data)
```

## 🎯 关键设计决策

### 1. 为什么选择LLM而非传统量化？
- **适应性强**：LLM能理解复杂市场情境
- **快速迭代**：修改Prompt比修改策略代码快
- **多因子融合**：自然语言天然支持多维度分析
- **可解释性**：LLM可以输出决策理由

### 2. 为什么完全复刻nof1.ai的Prompt格式？
- **经过验证**：nof1.ai已在实盘运行
- **数据完整**：包含短期+长期趋势
- **格式稳定**：LLM对固定格式理解更好

### 3. 为什么用2.6分钟决策间隔？
- **匹配nof1.ai**：1500次调用/3956分钟 ≈ 2.6分钟
- **平衡成本**：避免过度API调用
- **适合3分钟K线**：每根K线一次决策

### 4. 为什么强制模拟交易优先？
- **安全第一**：避免未测试系统直接操作真实资金
- **策略验证**：积累足够样本评估AI表现
- **参数调优**：找到最佳风控参数

## 🚀 扩展性设计

### 未来增强方向

#### 1. 多策略融合
```python
class MultiStrategyEngine:
    strategies = [
        LLMStrategy(),      # LLM决策
        MomentumStrategy(), # 动量策略
        MeanReversionStrategy() # 均值回归
    ]
    
    def aggregate_signals(self):
        # 投票机制或加权融合
        pass
```

#### 2. 链上数据集成
```python
class OnChainAnalyzer:
    async def get_whale_movements(coin):
        # Glassnode API: 大户资金流向
        pass
    
    async def get_exchange_flows(coin):
        # 交易所流入流出
        pass
```

#### 3. 情绪分析
```python
class SentimentAnalyzer:
    async def analyze_news(coin):
        # CryptoPanic / NewsAPI
        pass
    
    async def analyze_social(coin):
        # Twitter / Reddit情绪
        pass
```

## 📝 总结

本系统通过深度分析nof1.ai的运行机制，构建了一个**真正可盈利**的AI驱动交易系统：

1. **数据层**：完整的市场数据采集和处理
2. **AI层**：基于LLM的智能决策引擎
3. **执行层**：可靠的订单执行和仓位管理
4. **风控层**：多层次风险保护机制

关键创新是**用LLM替代传统策略代码**，让AI"理解"市场而非机械执行规则。

