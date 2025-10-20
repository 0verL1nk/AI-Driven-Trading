# 启动前检查清单

## ✅ 环境准备

- [ ] Python 3.10+ 已安装
  ```bash
  python3 --version
  ```

- [ ] 虚拟环境已创建
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

- [ ] 依赖已安装
  ```bash
  pip install -r requirements.txt
  ```

- [ ] TA-Lib已安装（如需使用）
  ```bash
  # Ubuntu/Debian
  sudo apt-get install ta-lib
  pip install TA-Lib
  ```

## ✅ 配置文件

- [ ] `.env` 文件已创建
  ```bash
  cp .env.example .env
  ```

- [ ] API密钥已填写
  - [ ] `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`
  - [ ] `BINANCE_API_KEY` (实盘交易时)
  - [ ] `BINANCE_API_SECRET` (实盘交易时)

- [ ] 交易配置已检查 (`config/trading_config.yaml`)
  - [ ] `trading_pairs` - 交易对列表
  - [ ] `ai.provider` - AI提供商
  - [ ] `ai.model` - AI模型
  - [ ] `paper_trading.enabled` - **确保为true**
  - [ ] `paper_trading.initial_balance` - 初始资金

- [ ] 风险参数已检查 (`config/risk_params.yaml`)
  - [ ] `max_risk_per_trade_percent` ≤ 2%
  - [ ] `leverage.max` ≤ 15
  - [ ] `min_risk_reward_ratio` ≥ 1.5

## ✅ 系统测试

- [ ] 配置检查通过
  ```bash
  python scripts/check_config.py
  ```

- [ ] 系统测试通过
  ```bash
  python test_system.py
  ```

- [ ] 示例Prompt生成成功
  ```bash
  python scripts/generate_sample_prompt.py
  ```

## ✅ API余额检查

- [ ] OpenAI账户有余额
  - 访问: https://platform.openai.com/usage
  - 预估费用: ~$30-50/天（每2.6分钟决策）

- [ ] Binance账户准备就绪（实盘时）
  - API权限已启用
  - IP白名单已配置（如需要）

## ✅ 监控准备

- [ ] 日志目录已创建
  ```bash
  mkdir -p logs
  ```

- [ ] 可以查看实时日志
  ```bash
  tail -f logs/trading.log
  ```

## ✅ 安全检查

- [ ] `.env` 文件权限正确
  ```bash
  chmod 600 .env
  ```

- [ ] `.env` 已加入 `.gitignore`
  ```bash
  grep ".env" .gitignore
  ```

- [ ] 使用Paper Trading测试
  - **切勿直接使用实盘！**
  - 至少测试1-2周

## ✅ 理解系统

- [ ] 已阅读 `README.md`
- [ ] 已阅读 `QUICKSTART.md`
- [ ] 了解风险提示
- [ ] 理解系统工作原理

## 📋 启动步骤

完成所有检查后：

### 方式1：使用启动脚本（推荐）

```bash
chmod +x run.sh
./run.sh
```

### 方式2：直接启动

```bash
source venv/bin/activate
python main.py
```

### 方式3：后台运行

```bash
nohup python main.py > logs/nohup.out 2>&1 &
```

## 🛑 停止系统

- **前台运行**: 按 `Ctrl+C`
- **后台运行**: 
  ```bash
  ps aux | grep main.py
  kill <PID>
  ```

## 📊 监控指标

启动后关注：

- [ ] 日志正常输出
- [ ] AI决策成功返回
- [ ] 数据采集无错误
- [ ] 订单执行正常（Paper Trading）

## ⚠️ 常见问题

### 1. ImportError: No module named 'talib'

```bash
# 安装TA-Lib库
sudo apt-get install ta-lib
pip install TA-Lib
```

### 2. OpenAI API Error

```bash
# 检查API密钥
python scripts/check_config.py

# 检查余额
# 访问 https://platform.openai.com/usage
```

### 3. 系统不交易

可能原因：
- AI判断市场条件不满足
- 风险参数过于严格
- 这是正常的！AI会保守

### 4. 日志文件过大

```bash
# 清理旧日志
rm logs/trading.log.*.gz
```

## 🎯 首次运行建议

1. **从小资金开始** (Paper Trading $1000)
2. **观察至少24小时**
3. **查看AI决策日志**
4. **分析交易逻辑**
5. **调整参数优化**
6. **运行1-2周后考虑实盘**

## 📞 需要帮助？

- 查看 `docs/` 目录文档
- 运行 `python test_system.py`
- 检查 `logs/trading.log`

---

**准备好了吗？开始交易吧！🚀**

记住：
- ✅ Paper Trading模式
- ✅ 小资金测试
- ✅ 持续监控
- ✅ 理解风险

