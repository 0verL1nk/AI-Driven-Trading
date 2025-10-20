# AI-Driven Cryptocurrency Trading System

基于 [nof1.ai](https://nof1.ai) 架构分析构建的AI驱动加密货币交易系统。

## 🎯 系统特点

### 核心创新
- **LLM驱动决策**：使用GPT-4/Claude等大语言模型替代传统量化策略
- **nof1.ai格式Prompt**：完全按照nof1.ai的实际格式构建Prompt
- **增强数据源**：技术指标 + 链上数据 + 市场情绪
- **风险优先**：严格的风控参数和止损机制
- **模拟交易**：支持Paper Trading测试策略

### 系统架构

```
数据采集层 → 数据处理层 → AI决策引擎 → 交易执行层
     ↓            ↓              ↓            ↓
  实时行情    技术指标      LLM推理      订单管理
  链上数据    信号融合    风险评估      仓位管理
  资金费率    Prompt构建  决策验证      回测引擎
```

## 📦 安装

### 1. 克隆项目

```bash
cd /home/ling/Trade
```

### 2. 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的API密钥：

```env
# 交易所API（用于实盘交易）
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here

# AI模型API
OPENAI_API_KEY=your_openai_key

# 或使用 Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_key

# 是否启用模拟交易
ENABLE_PAPER_TRADING=true
```

## 🚀 使用指南

### 快速开始（模拟交易）

```bash
python main.py
```

系统将以Paper Trading模式启动，使用虚拟资金进行交易测试。

### 配置交易参数

编辑 `config/trading_config.yaml`：

```yaml
# 修改交易对
trading_pairs:
  - BTC/USDT:USDT
  - ETH/USDT:USDT
  # 添加更多...

# 修改AI决策频率（分钟）
ai:
  decision_interval_minutes: 2.6  # 匹配nof1.ai

# 修改模拟交易初始资金
paper_trading:
  initial_balance: 10000.0  # USDT
```

编辑 `config/risk_params.yaml`：

```yaml
# 修改风险参数
position_sizing:
  max_risk_per_trade_percent: 2.0  # 每笔最大风险2%
  
leverage:
  min: 5
  max: 15  # 最大15倍杠杆
```

### 切换到实盘交易

⚠️ **警告：实盘交易有风险，请先充分测试！**

1. 修改 `.env`：
```env
ENABLE_PAPER_TRADING=false
```

2. 确保Binance API权限：
   - 启用期货交易
   - 启用提现（如需）
   - IP白名单配置

3. 小资金测试：
```yaml
# config/trading_config.yaml
paper_trading:
  initial_balance: 100.0  # 先用小资金测试
```

## 📊 系统运行逻辑

### 决策循环（每2.6分钟）

1. **数据采集**
   - 获取6种币的3分钟K线（最近10根）
   - 获取4小时K线（长期趋势）
   - 计算技术指标（EMA, MACD, RSI, ATR）
   - 获取资金费率和持仓量

2. **Prompt构建**
   - 格式化为nof1.ai格式
   - 包含所有币种的完整数据
   - 添加账户状态和持仓信息

3. **AI决策**
   - 调用GPT-4/Claude分析市场
   - 返回JSON格式的交易决策
   - 包含：信号类型、止损、止盈、杠杆、置信度

4. **决策验证**
   - 检查风险参数（最大风险2%）
   - 验证止损/止盈合理性
   - 确保风险回报比 > 1.5:1

5. **交易执行**
   - 开仓：市价单 + 止损单 + 止盈单
   - 平仓：检查失效条件自动平仓
   - 持仓：监控止损/止盈触发

### AI决策示例

输入Prompt（节选）：
```
ALL BTC DATA
current_price = 110909.5, current_ema20 = 111159.342, current_macd = -33.349, current_rsi (7 period) = 38.262

Open Interest: Latest: 27168.64 Average: 27024.58
Funding Rate: -2.2341e-06

Mid prices: [111297.0, 111249.5, 111322.0, ...]
RSI indicators (7‑Period): [54.336, 48.928, 55.775, ...]
```

AI输出决策（JSON）：
```json
{
  "BTC": {
    "trade_signal_args": {
      "coin": "BTC",
      "signal": "entry",
      "quantity": 0.1,
      "profit_target": 115000,
      "stop_loss": 109000,
      "invalidation_condition": "If the price closes below 108000 on a 3-minute candle",
      "leverage": 10,
      "confidence": 0.75,
      "risk_usd": 200
    },
    "justification": "RSI oversold + negative funding (bullish) + 4H trend up"
  }
}
```

## 📁 项目结构

```
Trade/
├── config/                  # 配置文件
│   ├── trading_config.yaml  # 交易配置
│   └── risk_params.yaml     # 风险参数
├── src/
│   ├── config.py           # 配置加载
│   ├── data/               # 数据采集层
│   │   ├── exchange_client.py    # 交易所客户端
│   │   └── indicator_engine.py   # 技术指标计算
│   ├── ai/                 # AI决策引擎
│   │   ├── prompt_builder.py     # Prompt构建
│   │   ├── llm_interface.py      # LLM接口
│   │   └── decision_validator.py # 决策验证
│   ├── execution/          # 交易执行层
│   │   ├── order_manager.py      # 订单管理
│   │   ├── portfolio_manager.py  # 仓位管理
│   │   └── paper_trading.py      # 模拟交易
│   └── trading_bot.py      # 主交易逻辑
├── main.py                 # 程序入口
├── requirements.txt        # Python依赖
└── README.md              # 本文件
```

## 🔧 技术栈

- **Python 3.10+**
- **CCXT**：交易所API统一接口
- **Pandas + TA-Lib**：技术指标计算
- **OpenAI / Anthropic**：LLM决策
- **AsyncIO**：异步并发处理

## ⚠️ 风险提示

1. **加密货币交易高风险**：可能损失全部本金
2. **AI决策非万能**：LLM可能产生错误决策
3. **先模拟后实盘**：充分测试再使用真实资金
4. **控制仓位**：单笔风险 < 2%，总仓位 < 3倍
5. **监控系统**：定期检查日志和性能

## 📈 性能监控

查看交易日志：
```bash
tail -f logs/trading.log
```

关键指标：
- **总收益率**：相对初始资金的回报
- **夏普比率**：风险调整后收益
- **胜率**：盈利交易占比
- **最大回撤**：从峰值到谷底的最大跌幅

## 🛠️ 开发计划

- [ ] Web Dashboard（实时监控）
- [ ] Telegram机器人通知
- [ ] 链上数据集成（Glassnode）
- [ ] 新闻情绪分析
- [ ] 多策略组合
- [ ] 回测引擎优化

## 📄 License

MIT License

## 🙏 致谢

本项目灵感来源于 [nof1.ai](https://nof1.ai) 的架构设计。

