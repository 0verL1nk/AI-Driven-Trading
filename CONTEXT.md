# 🤖 AI Trading Bot - 项目上下文总览

> **快速上下文恢复文档** - 用于新对话时快速了解项目全貌

## 📌 项目定位

**基于 nof1.ai 架构的 AI 驱动加密货币交易系统**

- ✅ 100% 复刻 nof1.ai 的交易逻辑和 Prompt 格式
- ✅ 使用 LLM（DeepSeek-R1/GPT-4）进行市场分析和交易决策
- ✅ 支持 Paper Trading（模拟交易）和 Live Trading（实盘交易）
- ✅ 完整的风险管理和监控系统
- ✅ Next.js 黑白简约 Web 监控界面

---

## 🏗️ 核心架构

### 系统组成

```
┌─────────────────────┐
│  Next.js Frontend   │ ← 监控界面 (localhost:3000)
│   (黑白简约UI)      │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│  FastAPI Backend    │ ← Web API (localhost:8000)
│  (web_monitor.py)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SQLite Database    │ ← 存储所有数据
│ (trading_data.db)   │
└──────────▲──────────┘
           │
           │ 保存数据
           │
┌──────────┴──────────┐
│   Trading Bot       │ ← 主程序 (main.py)
│  (trading_bot.py)   │
├─────────────────────┤
│ • Data Collection   │ ← WebSocket + CCXT
│ • AI Decision       │ ← LLM (Pydantic验证)
│ • Risk Management   │ ← 多层风控
│ • Order Execution   │ ← Paper/Live
└─────────────────────┘
```

### 交易循环（每 2.6 分钟）

```
1. 数据采集 → 6种币的K线、指标、资金费率
2. 账户状态 → 余额、持仓、收益率
3. 失效检查 → 检查并平仓失效仓位
4. 构建Prompt → nof1.ai格式 + Pydantic格式说明
5. AI决策 → LLM分析 → Pydantic验证
6. 风控验证 → 检查杠杆、风险、R/R比
7. 执行交易 → 开仓/平仓/持仓
8. 性能记录 → 保存到数据库
```

---

## 📁 项目结构

### 关键目录

```
/home/ling/Trade/
├── main.py                      # 🚀 程序入口
├── web_monitor.py               # 🖥️ 监控API服务器
├── trading_data.db              # 💾 SQLite数据库
├── .env                         # 🔐 环境变量（API密钥）
├── requirements.txt             # 📦 Python依赖
│
├── config/
│   ├── trading_config.yaml      # ⚙️ 交易配置
│   └── risk_params.yaml         # 🛡️ 风险参数
│
├── src/
│   ├── trading_bot.py           # 🤖 核心交易机器人
│   │
│   ├── ai/                      # 🧠 AI决策引擎
│   │   ├── llm_interface.py     # LLM接口（OpenAI/Anthropic）
│   │   ├── prompt_builder.py    # Prompt构建（nof1.ai格式）
│   │   ├── decision_validator.py# 决策验证（风控）
│   │   ├── decision_models.py   # ⭐ Pydantic模型（NEW）
│   │   └── output_parser.py     # ⭐ 结构化输出解析（NEW）
│   │
│   ├── data/                    # 📊 数据层
│   │   ├── exchange_client.py   # CCXT交易所客户端
│   │   ├── websocket_client.py  # WebSocket实时数据
│   │   └── indicator_engine.py  # 技术指标计算
│   │
│   ├── execution/               # 💼 交易执行
│   │   ├── paper_trading.py     # 模拟交易引擎
│   │   ├── order_manager.py     # 订单管理
│   │   └── portfolio_manager.py # 仓位管理
│   │
│   ├── database/                # 💾 数据库
│   │   └── models.py            # SQLite ORM
│   │
│   └── config.py                # ⚙️ 配置管理
│
├── frontend/                    # 🎨 Next.js监控界面
│   ├── app/page.tsx             # 主页面
│   └── components/              # React组件
│
├── tests/                       # 🧪 测试
│   └── test_pydantic_parser.py  # ⭐ Pydantic解析测试（NEW）
│
└── docs/                        # 📚 文档
    ├── CONTEXT.md               # ⭐ 本文档（NEW）
    ├── ARCHITECTURE.md          # 架构设计
    ├── TRADING_LOGIC.md         # 交易逻辑
    └── ...
```

---

## 🆕 最近重大更新

### 2025-10-21: Pydantic + 结构化输出

**问题背景：**
- AI返回的JSON格式不稳定，经常解析失败
- 字段验证不完整，导致运行时错误
- Ctrl+C退出时有异常traceback

**解决方案：**

#### 1. 引入 Pydantic 模型验证
```python
# src/ai/decision_models.py
class TradeSignalArgs(BaseModel):
    """严格的类型验证"""
    coin: str
    signal: SignalType  # Enum: entry/hold/close_position/no_action
    leverage: int = Field(ge=5, le=15)
    confidence: float = Field(ge=0.5, le=1.0)
    risk_usd: float = Field(ge=0)
    profit_target: Optional[float]
    stop_loss: Optional[float]
    # ...
```

#### 2. 自定义输出解析器
```python
# src/ai/output_parser.py
class TradingDecisionParser:
    """
    支持多种JSON格式：
    1. 嵌套格式：{"BTC": {"trade_signal_args": {...}}}
    2. 扁平格式：{"BTC": {"coin": "BTC", "signal": "hold", ...}}
    3. Markdown包裹：```json {...} ```
    """
    def parse(self, text: str) -> Dict[str, Dict]:
        # 清理 → 提取JSON → Pydantic验证 → 标准化格式
```

#### 3. Prompt格式说明自动生成
```python
# src/ai/prompt_builder.py
def _format_account_section(...):
    # 自动添加Pydantic格式说明到Prompt
    section += trading_parser.get_format_instructions()
```

#### 4. 改进的异常处理
```python
# main.py
try:
    await bot.start()
except KeyboardInterrupt:
    await bot.shutdown()  # 优雅退出
except asyncio.CancelledError:
    await bot.shutdown()  # 处理任务取消
```

**效果：**
- ✅ AI输出格式验证成功率提升
- ✅ 自动兼容 nof1.ai 的扁平格式
- ✅ 更清晰的错误提示
- ✅ Ctrl+C 优雅退出（已部分修复）
- ✅ `no_action`信号时自动修正不合规字段（leverage=0 → 5, confidence<0.5 → 0.5）

---

## ⚙️ 核心配置

### 🎯 三种交易模式

| 模式 | 配置 | 订单去向 | 风险 | 用途 |
|------|------|---------|-----|------|
| **本地模拟** | `ENABLE_PAPER_TRADING=True` | 本地模拟 | ✅ 无风险 | 快速测试策略 |
| **Testnet** | `ENABLE_PAPER_TRADING=False`<br>`USE_TESTNET=True` | 币安Testnet | ✅ 无风险 | 测试API调用 |
| **真实交易** | `ENABLE_PAPER_TRADING=False`<br>`USE_TESTNET=False` | 币安真实平台 | ⚠️ **真金白银** | 实盘交易 |

### 环境变量 (.env)

**本地模拟模式（默认）：**
```bash
# AI API（必须）
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 交易模式
ENABLE_PAPER_TRADING=True   # 本地模拟
```

**Testnet模式（推荐测试）：**
```bash
# AI API
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 交易模式
ENABLE_PAPER_TRADING=False  # 关闭本地模拟
USE_TESTNET=True            # 使用Testnet

# Testnet API（从 https://testnet.binancefuture.com 获取）
BINANCE_API_KEY=testnet_key_here
BINANCE_API_SECRET=testnet_secret_here
```

**真实交易模式（谨慎！）：**
```bash
# AI API
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 交易模式
ENABLE_PAPER_TRADING=False
USE_TESTNET=False

# 真实API密钥
BINANCE_API_KEY=real_key_here
BINANCE_API_SECRET=real_secret_here
```

📖 **详细配置说明**：查看 `docs/TESTNET_SETUP.md`

### 交易配置 (config/trading_config.yaml)

```yaml
# 交易对
trading_pairs:
  - BTC/USDT:USDT
  - ETH/USDT:USDT
  - SOL/USDT:USDT
  - BNB/USDT:USDT
  - XRP/USDT:USDT
  - DOGE/USDT:USDT

# AI配置
ai:
  provider: openai
  model: deepseek-ai/DeepSeek-R1-0528-Qwen3-8B
  temperature: 0.3
  max_tokens: 4000
  decision_interval_minutes: 2.6

# Paper Trading
paper_trading:
  enabled: true
  initial_balance: 10000.0
  slippage_percent: 0.1
```

### 风险参数 (config/risk_params.yaml)

```yaml
position_sizing:
  max_risk_per_trade_percent: 2.0       # 单笔最大风险
  
leverage:
  min: 5
  max: 15
  default: 10

exit_strategy:
  min_risk_reward_ratio: 1.5            # 最小盈亏比

drawdown_protection:
  max_daily_drawdown_percent: 10.0      # 最大日回撤
```

---

## 🚀 快速启动

### 1. 启动交易机器人

```bash
cd /home/ling/Trade
source venv/bin/activate
python main.py
```

### 2. 启动监控系统

**后端API：**
```bash
python web_monitor.py  # http://localhost:8000
```

**前端UI：**
```bash
cd frontend
npm run dev  # http://localhost:3000
```

---

## 🔧 常见问题

### 1. AI返回格式错误

**症状：**
```
ERROR | Pydantic parsing error: Invalid JSON
ERROR | risk_usd: Input should be greater than 0
```

**解决：**
- ✅ 已添加 Pydantic 自动验证
- ✅ 兼容 `risk_usd=0` (no_action信号)
- ✅ Prompt中自动包含格式说明

### 2. Ctrl+C 退出报错

**症状：**
```
KeyboardInterrupt
asyncio.exceptions.CancelledError
RuntimeError: Event loop is closed
```

**状态：**
- ✅ 主要问题已修复（优雅shutdown）
- ⚠️ WebSocket关闭时仍有警告（不影响功能）

### 3. WebSocket连接失败

**症状：**
```
WARNING | WebSocket connection failed
```

**说明：**
- 正常现象，系统会自动回退到 REST API
- WebSocket仅用于实时价格，不影响核心功能

---

## 📊 数据流

```
Binance API
    │
    ├─→ WebSocket → 实时K线/Ticker
    │       ↓
    └─→ REST API → 历史数据/下单
            ↓
    ExchangeClient (CCXT)
            ↓
    IndicatorEngine → 计算技术指标
            ↓
    PromptBuilder → 构建nof1.ai格式Prompt
            ↓
    TradingLLM → 调用AI模型
            ↓
    TradingDecisionParser → Pydantic验证  ⭐ NEW
            ↓
    DecisionValidator → 风控检查
            ↓
    OrderManager → 执行交易
            ↓
    TradingDatabase → SQLite持久化
            ↓
    FastAPI → Web监控API
            ↓
    Next.js UI → 用户界面
```

---

## 🎯 nof1.ai 复刻要点

### 1. Prompt格式 100%匹配

```python
# src/ai/prompt_builder.py
"""
It has been {minutes} minutes since you started trading...

ALL BTC DATA
current_price = 110909.5, current_ema20 = 111159.342, ...

Mid prices: [111297.0, 111249.5, ...]
EMA indicators (20‑period): [111214.482, ...]
MACD indicators: [78.719, 71.945, ...]
...

HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE
Current Total Return (percent): 29.97%
...
"""
```

### 2. 失效条件机制

```python
# 不同于止损，失效条件基于策略逻辑
invalidation_condition = "If price closes below 105000 on 3-min candle"

# 触发时立即平仓，不等止损
if check_invalidation():
    immediate_close()
```

### 3. 2.6分钟决策间隔

```yaml
# config/trading_config.yaml
ai:
  decision_interval_minutes: 2.6  # 与nof1.ai一致
```

### 4. 多时间框架分析

- **短期**：3分钟K线（最近100根）
- **长期**：4小时K线（最近100根）

---

## 📈 性能监控

### 数据库表

```sql
-- 账户状态
account_state: total_value, total_return, num_positions, ...

-- 币种价格
coin_prices: symbol, price, rsi_14, macd, funding_rate, ...

-- AI决策
ai_decisions: coin, decision, leverage, confidence, risk_usd, ...

-- 持仓
positions: symbol, quantity, entry_price, unrealized_pnl, ...

-- 交易历史
trade_history: symbol, entry_price, exit_price, pnl, ...
```

### Web监控界面

- **顶部价格栏**：6个币种实时价格
- **账户图表**：总价值历史曲线
- **AI决策列表**：最近20条决策
- **持仓列表**：当前活跃仓位

---

## 🧪 测试

### Pydantic解析器测试

```bash
python tests/test_pydantic_parser.py
```

测试内容：
- ✅ 嵌套格式解析
- ✅ 扁平格式解析
- ✅ Markdown包裹解析
- ✅ nof1.ai真实格式
- ✅ Pydantic验证错误捕获

---

## 💡 开发提示

### 修改AI模型

```yaml
# config/trading_config.yaml
ai:
  provider: openai  # 或 anthropic
  model: "gpt-4-turbo-preview"  # 或其他模型
  base_url: ""  # 留空使用官方API
```

### 添加新的交易对

```yaml
# config/trading_config.yaml
trading_pairs:
  - BTC/USDT:USDT
  - YOUR_COIN/USDT:USDT  # 添加新币种
```

### 调整风险参数

```yaml
# config/risk_params.yaml
position_sizing:
  max_risk_per_trade_percent: 1.5  # 降低单笔风险

leverage:
  max: 10  # 降低最大杠杆
```

---

## 🔒 安全注意

1. **Never commit `.env`** - 包含API密钥
2. **Paper Trading 优先** - 至少测试1-2周
3. **小资金开始** - 实盘初期用最小资金
4. **持续监控** - 定期查看日志和性能

---

## 📞 快速诊断

### 系统无法启动？

```bash
# 1. 检查Python版本
python --version  # 需要 3.10+

# 2. 检查依赖
pip install -r requirements.txt

# 3. 检查配置
ls .env config/trading_config.yaml

# 4. 查看日志
tail -f logs/trading.log
```

### AI决策失败？

```bash
# 1. 检查API密钥
echo $OPENAI_API_KEY

# 2. 测试API连接
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     $OPENAI_BASE_URL/models

# 3. 查看Pydantic验证日志
# 日志中搜索 "Pydantic" 关键词
```

### 交易执行失败？

```bash
# 1. 确认是Paper Trading
cat .env | grep PAPER

# 2. 检查Binance API（实盘时）
# 确保API权限正确

# 3. 查看order_manager日志
# 搜索 "order_manager" 或 "execute"
```

---

## 📚 相关文档

- **README.md** - 项目总览和快速开始
- **ARCHITECTURE.md** - 详细架构设计
- **TRADING_LOGIC.md** - 交易逻辑详解
- **MONITOR_QUICKSTART.md** - 监控系统快速启动
- **THIRD_PARTY_API.md** - 第三方API使用指南
- **REASONING_MODELS.md** - 推理模型支持

---

## 🎓 学习路径

### 1. 理解系统（第1天）
- 阅读 README.md
- 查看 ARCHITECTURE.md
- 运行 Paper Trading

### 2. 深入代码（第2-3天）
- 研究 `trading_bot.py`
- 理解 `prompt_builder.py`
- 学习 Pydantic 模型

### 3. 优化配置（第4-7天）
- 调整风险参数
- 测试不同AI模型
- 优化Prompt

### 4. 实盘准备（第2周+）
- 累积足够测试数据
- 分析性能指标
- 小资金实盘

---

**最后更新：2025-10-21**
**版本：v1.0 (Pydantic + 结构化输出)**

