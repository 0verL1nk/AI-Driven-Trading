# 🚀 快速开始指南

## 5分钟启动AI交易系统

### 第一步：安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 第二步：配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件
nano .env  # 或使用你喜欢的编辑器
```

**最小配置（仅需模拟交易）：**

```env
# OpenAI API Key (必需)
OPENAI_API_KEY=sk-your-openai-key-here

# 启用模拟交易
ENABLE_PAPER_TRADING=true
```

### 第三步：测试系统

```bash
python test_system.py
```

如果看到 "🎉 All tests passed!"，说明系统正常。

### 第四步：启动交易

```bash
python main.py
```

## 🎉 完成！

系统现在会：
1. 每2.6分钟采集市场数据
2. 使用GPT-4分析6种加密货币（BTC, ETH, SOL, BNB, XRP, DOGE）
3. 在模拟环境中执行交易
4. 输出交易日志到终端和 `logs/trading.log`

## 📊 查看日志

```bash
# 实时查看日志
tail -f logs/trading.log

# 或者在另一个终端窗口运行
watch -n 1 'tail -20 logs/trading.log'
```

## ⚙️ 调整参数

### 修改交易对

编辑 `config/trading_config.yaml`:

```yaml
trading_pairs:
  - BTC/USDT:USDT
  - ETH/USDT:USDT
  # 添加或删除币种
```

### 修改初始资金

```yaml
paper_trading:
  initial_balance: 10000.0  # 改为你想要的金额
```

### 修改风险参数

编辑 `config/risk_params.yaml`:

```yaml
position_sizing:
  max_risk_per_trade_percent: 2.0  # 每笔交易最大风险

leverage:
  max: 15  # 最大杠杆倍数
```

## 🔴 切换到真实交易

⚠️ **警告：仅在充分测试后使用！**

1. 获取Binance API密钥
2. 修改 `.env`:
   ```env
   BINANCE_API_KEY=your_key
   BINANCE_API_SECRET=your_secret
   ENABLE_PAPER_TRADING=false
   ```
3. **从小资金开始测试！**

## 🛑 停止系统

按 `Ctrl+C` 优雅停止

## 📚 下一步

- 阅读 [README.md](README.md) 了解系统架构
- 查看 [config/](config/) 目录配置详情
- 监控系统表现，调整参数

## 💬 常见问题

**Q: 提示缺少TA-Lib？**

A: 安装TA-Lib:
```bash
# Ubuntu/Debian
sudo apt-get install ta-lib
pip install TA-Lib

# Mac
brew install ta-lib
pip install TA-Lib

# Windows: 下载预编译包
pip install TA-Lib‑0.4.28‑cp310‑cp310‑win_amd64.whl
```

**Q: OpenAI API调用失败？**

A: 检查：
1. API密钥是否正确
2. 账户是否有余额
3. 网络连接是否正常

**Q: 系统一直不交易？**

A: 可能原因：
1. 市场条件不满足AI的交易标准
2. 风险参数过于严格
3. AI选择保守策略（这是正常的！）

**Q: 如何提高交易频率？**

A: 修改 `config/trading_config.yaml`:
```yaml
ai:
  decision_interval_minutes: 1.0  # 降低到1分钟（不推荐）
```

**注意：过高频率可能产生过多API调用费用！**

