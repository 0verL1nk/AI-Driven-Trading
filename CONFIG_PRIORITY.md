# 配置优先级说明

## 📋 配置文件结构

系统使用**双层配置**设计：

```
.env                        # 环境变量（敏感信息）
config/
  ├── trading_config.yaml   # 交易配置
  └── risk_params.yaml      # 风险参数
```

## 🔐 敏感信息 → `.env`

所有API密钥和敏感信息存放在 `.env` 文件中：

```env
# 交易所密钥
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=xxx

# AI密钥
OPENAI_API_KEY=sk-xxx

# 可选：自定义API地址
OPENAI_BASE_URL=https://your-api.com/v1
```

**优势：**
- 不会被提交到Git
- 易于在不同环境切换
- 符合12-Factor App标准

## ⚙️ 交易配置 → `config/trading_config.yaml`

交易策略和系统配置存放在YAML文件中：

```yaml
# 交易对
trading_pairs:
  - BTC/USDT:USDT
  - ETH/USDT:USDT

# AI配置
ai:
  provider: "openai"
  model: "gpt-4-turbo-preview"
  base_url: ""  # 可选，也可用环境变量
  temperature: 0.3
  decision_interval_minutes: 2.6
```

**优势：**
- 可读性强
- 易于版本控制
- 团队协作友好

## 🎯 配置优先级

当同一项配置在多处定义时，优先级为：

### 1. Base URL配置优先级

```
环境变量 > YAML配置 > 默认值

OPENAI_BASE_URL (env)
  ↓ 如果未设置
config/trading_config.yaml 中的 ai.base_url
  ↓ 如果未设置
默认：https://api.openai.com/v1
```

**示例：**

```bash
# 场景1：两处都未配置
# 结果：使用官方API

# 场景2：仅YAML配置
# config/trading_config.yaml:
ai:
  base_url: "https://api.oneapi.com/v1"
# 结果：使用OneAPI

# 场景3：两处都配置
# .env:
OPENAI_BASE_URL=http://localhost:8000/v1
# config/trading_config.yaml:
ai:
  base_url: "https://api.oneapi.com/v1"
# 结果：使用本地API（环境变量优先）
```

### 2. AI模型配置

```
YAML配置 > 代码默认值

config/trading_config.yaml 中的 ai.model
  ↓ 如果未设置
代码默认：gpt-4-turbo-preview
```

### 3. 其他配置优先级

| 配置项 | 优先级 | 位置 |
|--------|--------|------|
| API密钥 | 仅环境变量 | `.env` |
| 交易对列表 | YAML | `config/trading_config.yaml` |
| 风险参数 | YAML | `config/risk_params.yaml` |
| Base URL | 环境变量 > YAML | `.env` 或 `trading_config.yaml` |
| 模型名称 | YAML | `trading_config.yaml` |
| 杠杆范围 | YAML | `risk_params.yaml` |

## 📝 推荐配置方式

### 方式1：环境变量 + YAML（推荐）

**适用场景：**
- 多环境部署（开发/测试/生产）
- 需要快速切换API
- Docker部署

```bash
# .env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://api.oneapi.com/v1
ENABLE_PAPER_TRADING=true
```

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "gpt-4-turbo-preview"
  base_url: ""  # 留空，使用环境变量
```

### 方式2：仅YAML（简单场景）

**适用场景：**
- 本地单机运行
- 配置不经常变化
- 不使用Docker

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "gpt-4-turbo-preview"
  base_url: "https://api.oneapi.com/v1"
```

注意：API密钥仍需在 `.env` 中配置！

### 方式3：混合（灵活）

**适用场景：**
- 开发环境用本地API
- 生产环境用官方API

```bash
# 开发环境 .env.development
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://localhost:8000/v1

# 生产环境 .env.production
OPENAI_API_KEY=sk-real-key
OPENAI_BASE_URL=  # 留空使用官方
```

## 🔧 配置验证

### 启动时检查

运行系统时会自动输出当前配置：

```bash
python main.py
```

输出示例：
```
================================================================================
SYSTEM CONFIGURATION
================================================================================
Environment: development
Paper Trading: ENABLED ✅

AI Configuration:
  Provider: openai
  Model: gpt-4-turbo-preview
  Base URL: https://api.oneapi.com/v1
  Source: Environment Variable (Third-party/Custom API)
  Temperature: 0.3
  Max Tokens: 4000
  Decision Interval: 2.6 minutes
...
```

### 手动检查

```bash
# 检查环境变量
cat .env

# 检查YAML配置
cat config/trading_config.yaml

# 运行配置检查工具
python scripts/check_config.py
```

## 📚 配置示例

### 示例1：使用官方OpenAI API

```bash
# .env
OPENAI_API_KEY=sk-proj-xxxxx
OPENAI_BASE_URL=  # 留空
```

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "gpt-4-turbo-preview"
  base_url: ""
```

### 示例2：使用OneAPI（国内中转）

```bash
# .env
OPENAI_API_KEY=sk-xxxxx  # OneAPI提供的密钥
OPENAI_BASE_URL=https://api.oneapi.com/v1
```

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "gpt-4"  # OneAPI支持的模型
  base_url: ""  # 使用环境变量
```

### 示例3：使用本地vLLM

```bash
# .env
OPENAI_API_KEY=EMPTY
OPENAI_BASE_URL=http://localhost:8000/v1
```

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "Qwen/Qwen2.5-72B-Instruct"
  base_url: ""
  temperature: 0.3
  max_tokens: 8000  # 本地模型可以更大
```

### 示例4：仅在YAML中配置

```bash
# .env
OPENAI_API_KEY=sk-xxxxx
# 不设置OPENAI_BASE_URL
```

```yaml
# config/trading_config.yaml
ai:
  provider: "openai"
  model: "gpt-4"
  base_url: "https://api.oneapi.com/v1"  # 直接在这里配置
```

## ⚠️ 常见错误

### 错误1：API密钥在YAML中

❌ **错误做法：**
```yaml
# config/trading_config.yaml
ai:
  api_key: "sk-xxxxx"  # 不要这样做！
```

✅ **正确做法：**
```bash
# .env
OPENAI_API_KEY=sk-xxxxx
```

### 错误2：Base URL格式错误

❌ **错误：**
```yaml
base_url: "api.oneapi.com/v1"  # 缺少协议
```

✅ **正确：**
```yaml
base_url: "https://api.oneapi.com/v1"
```

### 错误3：YAML语法错误

❌ **错误：**
```yaml
ai:
base_url: "xxx"  # 缩进错误
```

✅ **正确：**
```yaml
ai:
  base_url: "xxx"
```

## 🎯 快速参考

| 需求 | 配置方式 |
|------|---------|
| 切换API | 修改 `.env` 中的 `OPENAI_BASE_URL` |
| 切换模型 | 修改 `trading_config.yaml` 中的 `ai.model` |
| 调整风险 | 修改 `risk_params.yaml` |
| 更换交易对 | 修改 `trading_config.yaml` 中的 `trading_pairs` |
| 改决策频率 | 修改 `trading_config.yaml` 中的 `decision_interval_minutes` |

---

**记住：敏感信息用 `.env`，策略配置用 YAML！🚀**

