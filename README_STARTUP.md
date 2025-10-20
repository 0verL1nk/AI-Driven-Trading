# 启动时配置输出说明

## 📊 系统启动时会输出什么？

运行 `python main.py` 时，系统会自动输出完整的配置信息，帮助你确认系统设置是否正确。

## 🎯 输出示例

### 示例1：使用官方OpenAI API

```
================================================================================
AI-DRIVEN CRYPTOCURRENCY TRADING SYSTEM
Based on nof1.ai architecture
================================================================================

================================================================================
SYSTEM CONFIGURATION
================================================================================
Environment: development
Paper Trading: ENABLED ✅

AI Configuration:
  Provider: openai
  Model: gpt-4-turbo-preview
  Base URL: Official OpenAI API (https://api.openai.com/v1)
  Temperature: 0.3
  Max Tokens: 4000
  Decision Interval: 2.6 minutes

Trading Configuration:
  Trading Pairs: 6 pairs
    - BTC/USDT:USDT
    - ETH/USDT:USDT
    - SOL/USDT:USDT
    - BNB/USDT:USDT
    - XRP/USDT:USDT
    - DOGE/USDT:USDT

Risk Management:
  Max Risk per Trade: 2.0%
  Leverage Range: 5-15x
  Max Daily Drawdown: 10.0%

Paper Trading Settings:
  Initial Balance: $10,000.00 USDT
================================================================================
```

### 示例2：使用OneAPI（国内中转）

```
================================================================================
SYSTEM CONFIGURATION
================================================================================
Environment: development
Paper Trading: ENABLED ✅

AI Configuration:
  Provider: openai
  Model: gpt-4
  Base URL: https://api.oneapi.com/v1
  Source: Environment Variable (Third-party/Custom API)  ← 注意这里
  Temperature: 0.3
  Max Tokens: 4000
  Decision Interval: 2.6 minutes
...
```

### 示例3：使用本地vLLM

```
================================================================================
SYSTEM CONFIGURATION
================================================================================
Environment: development
Paper Trading: ENABLED ✅

AI Configuration:
  Provider: openai
  Model: Qwen/Qwen2.5-72B-Instruct
  Base URL: http://localhost:8000/v1
  Source: Config File (Third-party/Custom API)  ← 配置来源
  Temperature: 0.3
  Max Tokens: 8000
  Decision Interval: 2.6 minutes
...
```

## 🔍 配置来源说明

### Base URL配置来源

系统会明确显示Base URL的配置来源：

1. **"Official OpenAI API"** 
   - 未配置base_url
   - 使用官方 https://api.openai.com/v1

2. **"Environment Variable (Third-party/Custom API)"**
   - 来自 `.env` 文件的 `OPENAI_BASE_URL`
   - 优先级最高

3. **"Config File (Third-party/Custom API)"**
   - 来自 `config/trading_config.yaml` 的 `ai.base_url`
   - 环境变量未设置时使用

## ⚠️ 启动检查项

### 关键配置检查

启动时请特别关注以下几项：

1. **Paper Trading状态**
   ```
   Paper Trading: ENABLED ✅    ← 新手必须看到这个
   ```
   或
   ```
   Paper Trading: DISABLED ⚠️ (LIVE TRADING)  ← 警告！真实交易
   ```

2. **Base URL配置**
   ```
   Base URL: https://api.oneapi.com/v1  ← 确认是你想用的API
   Source: Environment Variable
   ```

3. **Model名称**
   ```
   Model: gpt-4-turbo-preview  ← 确认模型名称正确
   ```

4. **Trading Pairs**
   ```
   Trading Pairs: 6 pairs  ← 确认交易对数量和名称
   ```

## 🚨 常见问题诊断

### 问题1：显示官方API但想用第三方

**症状：**
```
Base URL: Official OpenAI API (https://api.openai.com/v1)
```

**原因：**
- `.env` 中的 `OPENAI_BASE_URL` 未设置或为空
- `config/trading_config.yaml` 中的 `base_url` 为空

**解决：**
```bash
# 编辑 .env
echo "OPENAI_BASE_URL=https://api.oneapi.com/v1" >> .env
```

### 问题2：显示第三方API但想用官方

**症状：**
```
Base URL: https://api.oneapi.com/v1
Source: Environment Variable
```

**解决：**
```bash
# 编辑 .env，注释或删除该行
# OPENAI_BASE_URL=https://api.oneapi.com/v1
```

### 问题3：Paper Trading未启用

**症状：**
```
Paper Trading: DISABLED ⚠️ (LIVE TRADING)
```

**解决：**
```bash
# 编辑 .env
ENABLE_PAPER_TRADING=true
```

### 问题4：配置来源不明确

**症状：**不确定base_url来自哪里

**诊断：**
```bash
# 检查环境变量
grep OPENAI_BASE_URL .env

# 检查YAML配置
grep base_url config/trading_config.yaml
```

## 📋 完整启动日志示例

```bash
$ python main.py

2025-10-20 18:30:00 | INFO     | __main__            | ================================================================================
2025-10-20 18:30:00 | INFO     | __main__            | AI-DRIVEN CRYPTOCURRENCY TRADING SYSTEM
2025-10-20 18:30:00 | INFO     | __main__            | Based on nof1.ai architecture
2025-10-20 18:30:00 | INFO     | __main__            | ================================================================================
2025-10-20 18:30:00 | INFO     | __main__            | 
================================================================================
2025-10-20 18:30:00 | INFO     | __main__            | SYSTEM CONFIGURATION
2025-10-20 18:30:00 | INFO     | __main__            | ================================================================================
2025-10-20 18:30:00 | INFO     | __main__            | Environment: development
2025-10-20 18:30:00 | INFO     | __main__            | Paper Trading: ENABLED ✅
2025-10-20 18:30:00 | INFO     | __main__            | 
2025-10-20 18:30:00 | INFO     | __main__            | AI Configuration:
2025-10-20 18:30:00 | INFO     | __main__            |   Provider: openai
2025-10-20 18:30:00 | INFO     | __main__            |   Model: gpt-4-turbo-preview
2025-10-20 18:30:00 | INFO     | __main__            |   Base URL: https://api.oneapi.com/v1
2025-10-20 18:30:00 | INFO     | __main__            |   Source: Environment Variable (Third-party/Custom API)
2025-10-20 18:30:00 | INFO     | __main__            |   Temperature: 0.3
2025-10-20 18:30:00 | INFO     | __main__            |   Max Tokens: 4000
2025-10-20 18:30:00 | INFO     | __main__            |   Decision Interval: 2.6 minutes
2025-10-20 18:30:00 | INFO     | __main__            | 
2025-10-20 18:30:00 | INFO     | __main__            | Trading Configuration:
2025-10-20 18:30:00 | INFO     | __main__            |   Trading Pairs: 6 pairs
2025-10-20 18:30:00 | INFO     | __main__            |     - BTC/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            |     - ETH/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            |     - SOL/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            |     - BNB/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            |     - XRP/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            |     - DOGE/USDT:USDT
2025-10-20 18:30:00 | INFO     | __main__            | 
2025-10-20 18:30:00 | INFO     | __main__            | Risk Management:
2025-10-20 18:30:00 | INFO     | __main__            |   Max Risk per Trade: 2.0%
2025-10-20 18:30:00 | INFO     | __main__            |   Leverage Range: 5-15x
2025-10-20 18:30:00 | INFO     | __main__            |   Max Daily Drawdown: 10.0%
2025-10-20 18:30:00 | INFO     | __main__            | 
2025-10-20 18:30:00 | INFO     | __main__            | Paper Trading Settings:
2025-10-20 18:30:00 | INFO     | __main__            |   Initial Balance: $10,000.00 USDT
2025-10-20 18:30:00 | INFO     | __main__            | ================================================================================
2025-10-20 18:30:00 | INFO     | __main__            | 
2025-10-20 18:30:01 | INFO     | src.execution.paper_trading | Running in PAPER TRADING mode
2025-10-20 18:30:01 | INFO     | src.ai.llm_interface | Using custom OpenAI-compatible API from env: https://api.oneapi.com/v1
2025-10-20 18:30:01 | INFO     | src.trading_bot  | ============================================================
2025-10-20 18:30:01 | INFO     | src.trading_bot  | AI TRADING BOT STARTING
2025-10-20 18:30:01 | INFO     | src.trading_bot  | ============================================================
...
```

## ✅ 启动前检查清单

在启动系统前，确认以下配置正确输出：

- [ ] Paper Trading状态（新手必须ENABLED）
- [ ] AI Provider和Model名称
- [ ] Base URL（官方或第三方）
- [ ] Base URL来源（环境变量或配置文件）
- [ ] 交易对列表
- [ ] 风险参数（Max Risk, Leverage, Drawdown）
- [ ] 初始资金（Paper Trading）

## 🔧 调试技巧

### 查看完整日志

```bash
# 实时查看
tail -f logs/trading.log

# 查看启动日志
head -50 logs/trading.log
```

### 验证配置

```bash
# 运行配置检查工具
python scripts/check_config.py

# 测试第三方API连接
python scripts/test_third_party_api.py
```

---

**启动系统前，仔细查看配置输出，确保一切正确！🚀**

