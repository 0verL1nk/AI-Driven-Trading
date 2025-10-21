# 🤖 AI-Driven Cryptocurrency Trading System

基于nof1.ai架构的AI驱动加密货币交易系统，支持模拟交易和实盘交易。

## ✨ 核心特性

- **🧠 AI决策引擎** - 使用DeepSeek-R1等LLM模型进行市场分析和交易决策
- **📊 实时市场数据** - WebSocket + CCXT双重数据源，确保数据实时性和稳定性
- **📈 技术指标分析** - EMA, MACD, RSI, ATR, 布林带等多种指标
- **🎯 风险管理** - 自动止损、止盈、仓位管理
- **💰 Paper Trading** - 模拟交易环境，零风险测试策略
- **🖥️ Web监控界面** - Next.js黑白简约风格实时监控面板
- **💾 数据持久化** - SQLite数据库存储所有交易数据和AI决策

## 🏗️ 系统架构

```
┌─────────────────────┐
│   Next.js Frontend  │  ← 黑白简约UI
│   (localhost:3000)  │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   FastAPI Backend   │
│   (localhost:8000)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SQLite Database    │  ← 存储所有数据
│ (trading_data.db)   │
└──────────▲──────────┘
           │
           │ 保存数据
           │
┌──────────┴──────────┐
│   Trading Bot       │
│   (main.py)         │
├─────────────────────┤
│ • Market Data       │  ← WebSocket + CCXT
│ • AI Decision       │  ← DeepSeek-R1
│ • Risk Management   │
│ • Paper Trading     │
└─────────────────────┘
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/ling/Trade
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```bash
# AI模型配置（必须）
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# Paper Trading已启用，Binance API密钥可选
ENABLE_PAPER_TRADING=true
```

### 3. 运行交易机器人

```bash
python main.py
```

### 4. 启动监控界面

**后端API：**
```bash
python web_monitor.py
```

**前端UI：**
```bash
cd frontend
npm install  # 首次运行
npm run dev
```

访问：http://localhost:3000

## 📁 项目结构

```
/home/ling/Trade/
├── main.py                     # 交易机器人入口
├── web_monitor.py              # Web监控API服务器
├── trading_data.db             # SQLite数据库
├── requirements.txt            # Python依赖
├── .env                        # 环境变量配置
│
├── config/
│   └── trading_config.yaml    # 交易参数配置
│
├── src/
│   ├── ai/                    # AI决策引擎
│   │   ├── llm_interface.py  # LLM接口
│   │   ├── prompt_builder.py # Prompt构建
│   │   └── decision_validator.py
│   │
│   ├── data/                  # 数据层
│   │   ├── exchange_client.py    # CCXT交易所客户端
│   │   ├── websocket_client.py   # WebSocket实时数据
│   │   ├── indicator_engine.py   # 技术指标计算
│   │   └── market_data.py
│   │
│   ├── execution/             # 交易执行
│   │   ├── paper_trading.py  # 模拟交易引擎
│   │   ├── order_manager.py
│   │   └── portfolio_manager.py
│   │
│   ├── database/              # 数据库
│   │   └── models.py
│   │
│   └── config.py              # 配置管理
│
└── frontend/                  # Next.js监控界面
    ├── app/
    │   ├── page.tsx          # 主页面
    │   └── layout.tsx
    ├── components/
    │   ├── PriceBar.tsx      # 价格栏
    │   ├── AccountChart.tsx  # 账户图表
    │   ├── DecisionsList.tsx # AI决策列表
    │   └── PositionsList.tsx # 持仓列表
    └── lib/
        └── api.ts            # API调用
```

## ⚙️ 配置说明

### Trading Config (`config/trading_config.yaml`)

```yaml
# 交易对
trading_pairs:
  - BTC/USDT:USDT
  - ETH/USDT:USDT
  - SOL/USDT:USDT

# AI配置
ai:
  model: "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
  temperature: 0.3
  decision_interval_minutes: 2.6

# Paper Trading
paper_trading:
  enabled: true
  initial_balance: 10000.0
  slippage_percent: 0.1
```

### Environment Variables (`.env`)

```bash
# AI API
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# Trading Mode
ENABLE_PAPER_TRADING=true

# Binance API (真实交易时需要)
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

## 📊 监控界面功能

### 🎨 黑白简约设计

- **顶部价格栏** - 实时显示6个交易对价格
- **账户价值图表** - 显示账户总价值历史曲线
- **AI决策列表** - 最近20条AI交易决策记录
- **持仓列表** - 当前所有活跃持仓

### 🔄 数据更新

- 前端每5秒自动刷新
- WebSocket实时价格推送
- 交易bot每2.6分钟执行决策

## 🛠️ 开发指南

### 修改AI模型

编辑 `config/trading_config.yaml`:

```yaml
ai:
  model: "gpt-4-turbo-preview"  # 或其他模型
  base_url: ""  # 留空使用官方API
```

### 调整风险参数

```yaml
risk_management:
  max_risk_per_trade: 2.0     # 每笔最大风险2%
  leverage_range: [5, 15]     # 杠杆范围5-15x
  max_daily_drawdown: 10.0    # 最大回撤10%
```

### 切换到真实交易

1. 获取Binance API密钥
2. 配置 `.env` 文件
3. 修改 `.env`: `ENABLE_PAPER_TRADING=false`
4. 修改 `config/trading_config.yaml`: `paper_trading.enabled: false`

⚠️ **警告：真实交易有风险！**

## 🔧 故障排除

### WebSocket连接失败
- 正常现象，系统会回退到REST API
- WebSocket仅用于实时价格监控，不影响核心功能

### IP被封禁 (HTTP 418)
- Binance的频率限制
- 系统会自动重试（最多3次，间隔递增）
- 等待几分钟后自动恢复

### 前端无法连接后端
- 确保后端API在运行: `curl http://localhost:8000/api/account`
- 检查CORS配置

### 数据库为空
- 正常！首次运行时数据库是空的
- 运行交易bot后会自动填充数据

## 📝 文档

- [快速启动指南](MONITOR_QUICKSTART.md)
- [监控系统说明](RUN_MONITOR.md)
- [API文档](http://localhost:8000/docs) (运行后访问)

## 🎯 主要功能

### AI决策流程

1. **数据收集** - 实时K线、技术指标、资金费率
2. **Prompt构建** - 按nof1.ai格式组织数据
3. **AI分析** - LLM分析市场并给出决策
4. **风险验证** - 验证决策是否符合风险参数
5. **执行交易** - Paper模式模拟执行，Live模式真实执行
6. **监控记录** - 所有数据保存到数据库

### 数据流

```
Binance API → WebSocket/REST → Market Data
                                     ↓
              Technical Indicators ← IndicatorEngine
                                     ↓
                        Prompt Builder → AI Model
                                              ↓
                            Decision Validator ← Risk Rules
                                              ↓
                           Paper/Live Trading ← Order Manager
                                              ↓
                             Database ← Trading History
                                              ↓
                                    Web API ← Monitor UI
```

## 🌟 特色功能

- ✅ **支持推理模型** - 自动处理`<think></think>`标签
- ✅ **第三方API** - 支持任何OpenAI兼容API
- ✅ **实时监控** - 黑白简约Web界面
- ✅ **完整记录** - 所有决策和交易数据持久化
- ✅ **风险管理** - 多层风险控制机制
- ✅ **灵活配置** - YAML + ENV双重配置

## 📞 支持

遇到问题？查看：
- [故障排除文档](MONITOR_QUICKSTART.md#-故障排除)
- [系统日志](logs/)
- [数据库查询](MONITOR_QUICKSTART.md#-数据库位置)

---

## 📜 许可证

本项目仅供学习和研究使用。

⚠️ **免责声明**：加密货币交易有风险，使用本系统进行真实交易时请谨慎。作者不对任何交易损失负责。
