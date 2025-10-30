# 🤖 AI-Driven Cryptocurrency Trading System

基于nof1.ai架构的AI驱动加密货币交易系统，支持模拟交易和实盘交易。预览网址: https://ai-driven-trading.vercel.app/

## ✨ 核心特性

- **🧠 AI决策引擎** - 智能区分推理模型和普通模型，自动适配调用策略
  - **推理模型**（DeepSeek-R1, o1等）- 一步生成思考+决策
  - **普通模型**（GPT-4, Claude等）- 两步调用（先思考分析，再输出JSON）
- **💭 思考过程记录** - 完整保存AI思考过程到数据库，支持回溯分析
- **📊 实时市场数据** - WebSocket + CCXT双重数据源，确保数据实时性和稳定性
- **📈 技术指标分析** - EMA, MACD, RSI, ATR, 布林带等多种指标
- **🎯 风险管理** - 自动止损、止盈、仓位管理
- **💰 Paper Trading** - 模拟交易环境，零风险测试策略
- **🖥️ Web监控界面** - Next.js黑白简约风格实时监控面板
  - 智能数据采样，大数据量下依然流畅
  - 自动时区转换（UTC+8）
  - 动态坐标格式化（5k, 10k, 1.5M）
- **💾 数据持久化** - SQLite/MySQL 数据库存储所有交易数据和AI决策
- **🐳 Docker 支持** - 一键部署，生产环境就绪
- **⚡ UV 包管理** - 极速依赖安装（比 pip 快 10-100 倍）

## 🏗️ 系统架构

```
┌─────────────────────┐
│   Next.js Frontend  │  ← 黑白简约UI
│   (localhost:3000)  │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│   FastAPI Backend    │
│   (localhost:8541)   │  ← 集成在交易bot中
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SQLite/MySQL DB    │  ← 存储所有数据
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
│ • Web API Server    │  ← 内置FastAPI
└─────────────────────┘
```

## 🚀 快速开始

### 方式1: 使用 uv（推荐，更快）

```bash
# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 使用快速启动脚本
./quickstart.sh

# 或手动安装
uv venv
source .venv/bin/activate  # Linux/macOS
uv pip install -r requirements.txt
```

### 方式2: 使用传统 pip

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
# 使用 uv（推荐）
uv run python main.py

# 或直接运行
python main.py

# 使用 MySQL（可选）
python main.py --db-type mysql \
  --db-host localhost \
  --db-port 3306 \
  --db-user root \
  --db-password your_password \
  --db-name trading_db
```

### 4. Docker 部署（推荐生产环境）

```bash
# 构建镜像
docker build -t ai-trading-bot .

# 运行容器（SQLite）
docker run -d \
  --name trading-bot \
  -p 8541:8541 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/trading_data.db:/app/trading_data.db \
  -v $(pwd)/config:/app/config \
  -e OPENAI_API_KEY=your_api_key \
  -e OPENAI_BASE_URL=https://api.siliconflow.cn/v1 \
  -e ENABLE_PAPER_TRADING=true \
  ai-trading-bot

# 或使用 Docker Compose
docker-compose up -d
```

详细 Docker 部署说明请查看 [DOCKER.md](DOCKER.md)

### 5. 启动监控界面

**后端API：**
后端已集成到交易bot中，无需单独启动（自动运行在 8541 端口）

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
├── pyproject.toml              # 项目配置（uv标准）
├── requirements.txt            # Python依赖
├── Dockerfile                  # Docker镜像构建
├── docker-compose.yml          # Docker Compose配置
├── quickstart.sh               # 快速启动脚本
├── trading_data.db             # SQLite数据库
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
│   ├── database/              # 数据库（ORM）
│   │   ├── models.py          # 数据库模型（SQLAlchemy）
│   │   ├── orm_models.py      # ORM模型定义
│   │   ├── session.py         # 数据库会话管理
│   │   └── adapter.py         # 数据库适配器
│   │
│   ├── web/                   # Web API服务
│   │   └── api_server.py      # FastAPI服务器
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
    │   ├── TradesList.tsx    # 交易历史（无限滚动）
    │   └── PositionsList.tsx # 持仓列表
    └── lib/
        ├── api.ts            # API调用
        └── utils.ts           # 工具函数
```

## ⚙️ 配置说明

### 数据库配置

项目支持两种数据库：

**SQLite（默认）**
```bash
python main.py --db-type sqlite --db-path trading_data.db
```

**MySQL（生产环境推荐）**
```bash
python main.py --db-type mysql \
  --db-host localhost \
  --db-port 3306 \
  --db-user root \
  --db-password your_password \
  --db-name trading_db
```

### Trading Config (`config/trading_config.yaml`)

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
  provider: "openai"  # openai, anthropic, local
  model: "deepseek-ai/deepseek-v3.1-terminus"
  is_reasoning_model: true  # 🔑 是否为推理模型
    # true: 推理模型（DeepSeek-R1, o1）- 一步生成思考+JSON
    # false: 普通模型（GPT-4, Claude）- 两步生成（先思考，再JSON）
  base_url: ""  # 第三方API地址（留空使用官方API）
  temperature: 0.3
  max_tokens: 9000
  decision_interval_minutes: 3
  
  # 可选参数
  stream: true  # 流式输出，用于提取reasoning_content
  
  # 推理模型专用参数（DeepSeek等）
  extra_body: 
    chat_template_kwargs: 
      thinking: true  # 启用推理模式

# Paper Trading
paper_trading:
  enabled: true
  initial_balance: 10000.0
  slippage_percent: 0.1
  commission_percent: 0.04
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

- **顶部价格栏** - 实时显示6个交易对价格和24h涨跌幅
- **账户价值图表** - 智能采样历史曲线，支持6H/24H/72H/ALL时间范围
  - 动态坐标格式化（5k, 10k, 1.5M）
  - 自动时区转换（UTC+8）
  - 快速加载（最多200点）
- **AI决策列表** - 最近20条决策记录
  - 显示入场价、止损、止盈、杠杆、置信度
  - **可展开查看AI思考过程** 💭
- **持仓列表** - 当前所有活跃持仓，实时盈亏
- **交易历史** - 已完成交易的详细记录

### 🔄 数据更新

- 前端每3秒自动刷新账户图表
- 价格栏每5秒更新
- WebSocket实时价格推送（如果可用）
- 交易bot每3分钟执行决策

## 🛠️ 开发指南

### 切换AI模型

编辑 `config/trading_config.yaml`:

**使用推理模型（DeepSeek-R1, o1等）**
```yaml
ai:
  model: "deepseek-ai/deepseek-v3.1-terminus"
  is_reasoning_model: true  # 推理模型
  base_url: "https://api.siliconflow.cn/v1"
  stream: true
  extra_body: 
    chat_template_kwargs: 
      thinking: true
```

**使用普通模型（GPT-4, Claude等）**
```yaml
ai:
  model: "gpt-4-turbo-preview"
  is_reasoning_model: false  # 普通模型，采用两步调用
  base_url: ""  # 留空使用OpenAI官方API
  stream: true
```

**使用Claude**
```yaml
ai:
  provider: "anthropic"
  model: "claude-3-opus-20240229"
  is_reasoning_model: false
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

## 🐳 Docker 部署

### 快速开始

```bash
# 使用 Docker Compose（推荐）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量配置

创建 `.env` 文件或使用 `docker-compose.yml` 中的环境变量：

```bash
# AI API（必需）
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 数据库配置
DB_TYPE=sqlite  # 或 mysql
DB_PATH=trading_data.db

# MySQL配置（如果使用MySQL）
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=trading_db

# 交易配置
ENABLE_PAPER_TRADING=true
USE_TESTNET=false
```

详细说明请查看 [DOCKER.md](DOCKER.md)

## 🔧 故障排除

### Docker 相关问题

**容器无法启动**
```bash
# 查看日志
docker logs trading-bot

# 检查环境变量
docker exec trading-bot env | grep OPENAI
```

**数据库连接失败（MySQL）**
- 确认 MySQL 服务运行中
- 检查网络连接：`docker network ls`
- 验证数据库凭据

### WebSocket连接失败
- 正常现象，系统会回退到REST API
- WebSocket仅用于实时价格监控，不影响核心功能

### IP被封禁 (HTTP 418)
- Binance的频率限制
- 系统会自动重试（最多3次，间隔递增）
- 等待几分钟后自动恢复

### 前端无法连接后端
- 确保后端API在运行: `curl http://localhost:8541/api/account`
- 检查CORS配置
- 确认端口：后端8541，前端3000

### 前端图表不显示数据
- 检查是否有历史数据：`sqlite3 trading_data.db "SELECT COUNT(*) FROM account_state;"`
- 启动交易bot运行一段时间后再查看
- 数据量少时会自动返回全部数据（已修复空结果bug）

### AI思考过程未保存
- 确认配置了 `is_reasoning_model` 和 `stream: true`
- 推理模型需要配置 `extra_body` 参数
- 查看数据库：`SELECT thinking FROM ai_decisions WHERE thinking IS NOT NULL LIMIT 1;`

### 时间显示不正确
- 系统已自动处理时区转换（UTC+8）
- 如需修改时区，编辑 `frontend/lib/utils.ts` 中的 `parseUTCTime` 函数

### 数据库为空
- 正常！首次运行时数据库是空的
- 运行交易bot后会自动填充数据

## 📝 文档

- [快速启动指南](MONITOR_QUICKSTART.md)
- [监控系统说明](RUN_MONITOR.md)
- [Docker 部署指南](DOCKER.md)
- [UV 使用指南](UV.md)
- [API文档](http://localhost:8541/docs) (运行后访问)

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

### 🧠 智能LLM调用策略

系统自动识别模型类型并采用最优调用策略：

**推理模型**（is_reasoning_model: true）
- 一步生成：模型自带推理能力，直接输出思考+JSON
- 支持模型：DeepSeek-R1, OpenAI o1, 等
- 自动提取 `reasoning_content` 或 `<think>` 标签
- 配置 `extra_body` 参数启用推理模式

**普通模型**（is_reasoning_model: false）
- 两步生成：
  1. **第一步** - 发送提示词，让模型思考分析市场
  2. **第二步** - 带上第一步的思考上下文，要求输出JSON决策
- 支持模型：GPT-4, Claude, GPT-3.5等
- 思考内容完整保存到数据库

### 📊 前端监控优化

**智能数据采样**
- `fast` 模式：最多200个点，大数据量秒加载
- `auto` 模式：根据时间范围自动调整密度（800-2000点）
- `full` 模式：完整曲线（谨慎使用）
- 修复了数据量少时返回空的bug

**动态坐标格式化**
- 自动根据数据范围选择最佳显示格式
- 小额交易：`$500`, `$750`
- 万元级别：`$5k`, `$10.5k`
- 十万级别：`$100k`, `$250k`
- 百万级别：`$1.5M`, `$2.3M`

**时区自动转换**
- 后端UTC时间自动转换为本地时间（UTC+8）
- 所有时间戳统一处理，避免混乱

### 💾 数据持久化

- ✅ **AI思考过程** - 完整保存到 `ai_decisions.thinking` 字段
- ✅ **交易历史** - 入场/出场时间、价格、盈亏
- ✅ **账户状态** - 每次决策后保存账户快照
- ✅ **市场数据** - 价格、指标、资金费率

### 🔧 其他特性

- ✅ **第三方API支持** - 任何OpenAI兼容API（硅基流动、OneAPI等）
- ✅ **实时监控** - 黑白简约Web界面，3秒自动刷新
- ✅ **风险管理** - 多层风险控制机制
- ✅ **灵活配置** - YAML + ENV双重配置

## 📞 支持

遇到问题？查看：
- [故障排除文档](MONITOR_QUICKSTART.md#-故障排除)
- [系统日志](logs/)
- [数据库查询](MONITOR_QUICKSTART.md#-数据库位置)

---

## 🆕 更新日志

### v2.2.0 (2025-01-28)

**🚀 项目管理和部署**
- ✨ 集成 `uv` 包管理器（比 pip 快 10-100 倍）
- ✨ 新增 `pyproject.toml` 项目配置
- ✨ Docker 支持（Dockerfile + docker-compose.yml）
- ✨ 快速启动脚本 `quickstart.sh`

**💾 数据库升级**
- ✨ 全面重构为 SQLAlchemy ORM
- ✨ 支持 SQLite 和 MySQL 双数据库
- ✨ 命令行参数选择数据库类型
- ✨ 自动数据库迁移和兼容性处理

**🔧 架构优化**
- ✨ Web API 服务解耦到独立模块
- ✨ 代码规范化，提高可维护性
- ✨ 优化日志输出，减少冗余信息

### v2.0.0 (2025-01-28)

**🧠 AI调用优化**
- ✨ 新增 `is_reasoning_model` 配置，智能区分推理模型和普通模型
- ✨ 推理模型：一步生成（DeepSeek-R1, o1）
- ✨ 普通模型：两步调用（GPT-4, Claude）- 先思考，再JSON
- ✨ 支持 `extra_body` 参数配置（推理模型专用）
- ✨ 完整保存AI思考过程到数据库

**📊 前端优化**
- 🐛 修复数据量少时图表不显示的bug
- ✨ 动态坐标格式化（5k, 10k, 1.5M）
- ✨ 智能数据采样（fast/auto/full模式）
- ✨ 自动时区转换（UTC+8）
- ✨ AI思考过程可展开查看
- ✨ 交易历史无限滚动优化

**🔧 技术改进**
- 📦 新增共享工具函数库 `frontend/lib/utils.ts`
- 🔧 优化数据库查询性能
- 📝 更新完整文档

---

## 📜 许可证

本项目仅供学习和研究使用。

⚠️ **免责声明**：加密货币交易有风险，使用本系统进行真实交易时请谨慎。作者不对任何交易损失负责。
