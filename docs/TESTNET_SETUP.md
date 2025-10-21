# 🧪 币安Testnet配置指南

## 📌 三种交易模式对比

| 模式 | 环境变量配置 | 订单去向 | 资金风险 | 适用场景 |
|------|------------|---------|---------|---------|
| **本地模拟** | `ENABLE_PAPER_TRADING=True` | 本地模拟（不发送） | ✅ 无风险 | 快速测试策略逻辑 |
| **Testnet模拟** | `ENABLE_PAPER_TRADING=False`<br>`USE_TESTNET=True` | 币安Testnet平台 | ✅ 无风险 | 测试真实API调用 |
| **真实交易** | `ENABLE_PAPER_TRADING=False`<br>`USE_TESTNET=False` | 币安真实平台 | ⚠️ **真金白银！** | 实盘交易 |

---

## 🎯 如何使用币安Testnet

### 步骤1: 获取Testnet API密钥

1. 访问币安期货Testnet平台：
   ```
   https://testnet.binancefuture.com
   ```

2. 使用任意邮箱注册（不需要真实信息）

3. 登录后，在右上角 **API Management** 生成API密钥：
   - API Key
   - Secret Key

4. 你会获得 **测试用的USDT**（模拟资金，无限量）

### 步骤2: 配置环境变量

创建 `.env` 文件（或导出环境变量）：

```bash
# 关闭本地模拟模式
ENABLE_PAPER_TRADING=False

# 启用Testnet模式
USE_TESTNET=True

# 填入Testnet的API密钥（不是真实平台的！）
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_key_here

# AI配置（保持不变）
OPENAI_API_KEY=your_openai_key
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
```

### 步骤3: 运行交易机器人

```bash
python main.py
```

你应该看到：
```
🧪 TESTNET Mode: Using Binance Futures Testnet
   URL: https://testnet.binancefuture.com
   ✅ Safe for testing - NO real money!
```

### 步骤4: 查看交易记录

登录 https://testnet.binancefuture.com 查看：
- 持仓
- 订单历史
- 资金变化
- 交易记录

---

## ⚙️ 完整配置示例

### `.env` 文件示例（Testnet模式）

```bash
# ==========================================
# 交易模式配置
# ==========================================
ENABLE_PAPER_TRADING=False  # 关闭本地模拟
USE_TESTNET=True            # 使用Testnet

# ==========================================
# 币安Testnet API配置
# ==========================================
# 从 https://testnet.binancefuture.com 获取
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_key_here

# ==========================================
# AI配置
# ==========================================
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# ==========================================
# 其他配置（可选）
# ==========================================
ENVIRONMENT=development
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## 🔍 验证配置是否正确

### 1. 检查启动日志

**正确配置（Testnet）：**
```
🧪 TESTNET Mode: Using Binance Futures Testnet
   URL: https://testnet.binancefuture.com
   ✅ Safe for testing - NO real money!
```

**错误配置（本地模拟）：**
```
📊 Paper Trading Mode: Using mainnet for real market data
   Orders will be simulated locally (not sent to exchange)
```

**危险配置（真实交易）：**
```
🔴 LIVE Trading Mode: Using authenticated API
⚠️  REAL MONEY AT RISK - Orders will be executed on mainnet!
```

### 2. 检查订单是否发送到Testnet

开仓后，访问 https://testnet.binancefuture.com：
- 点击 **Positions** 查看持仓
- 点击 **Open Orders** 查看挂单
- 点击 **Order History** 查看历史订单

如果能看到订单，说明配置成功！✅

---

## ❓ 常见问题

### Q1: 为什么Testnet看不到订单？

**可能原因：**
1. ✅ 检查 `ENABLE_PAPER_TRADING=False`（必须关闭本地模拟）
2. ✅ 检查 `USE_TESTNET=True`（必须启用Testnet）
3. ✅ 检查API密钥是否正确（从Testnet获取，不是真实平台）
4. ✅ 检查启动日志是否显示 `🧪 TESTNET Mode`

### Q2: Testnet余额不足怎么办？

Testnet会自动补充模拟资金，或者：
1. 访问 https://testnet.binancefuture.com
2. 右上角点击 **Faucet** 
3. 申请更多测试USDT

### Q3: 真实交易如何配置？

⚠️ **慎重！需要确保策略完全测试通过！**

```bash
ENABLE_PAPER_TRADING=False  # 关闭本地模拟
USE_TESTNET=False           # 关闭Testnet
BINANCE_API_KEY=your_real_api_key      # 真实API密钥
BINANCE_API_SECRET=your_real_secret    # 真实Secret
```

启动后会看到：
```
🔴 LIVE Trading Mode: Using authenticated API
⚠️  REAL MONEY AT RISK - Orders will be executed on mainnet!
```

### Q4: 如何快速切换模式？

使用环境变量快速切换：

```bash
# 本地模拟（最快）
ENABLE_PAPER_TRADING=True python main.py

# Testnet测试
ENABLE_PAPER_TRADING=False USE_TESTNET=True python main.py

# 真实交易（谨慎！）
ENABLE_PAPER_TRADING=False USE_TESTNET=False python main.py
```

---

## 📊 推荐测试流程

1. **本地模拟** (1-2天)
   - 验证AI输出格式正确
   - 验证交易逻辑正常
   - 快速迭代策略

2. **Testnet测试** (1-2周) 👈 **你在这里**
   - 验证API调用正确
   - 验证订单执行正常
   - 验证风控参数合理
   - 模拟真实市场环境

3. **小资金实盘** (2-4周)
   - 使用少量真实资金（如$100）
   - 验证策略在真实环境表现
   - 积累实盘数据

4. **正式实盘**
   - 逐步增加资金
   - 持续监控和优化

---

## 🔗 相关链接

- **Testnet平台**: https://testnet.binancefuture.com
- **Testnet文档**: https://testnet.binancefuture.com/en/support/faq
- **币安API文档**: https://binance-docs.github.io/apidocs/futures/cn/
- **CCXT文档**: https://docs.ccxt.com/

---

**祝测试顺利！🚀**

