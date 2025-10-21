# 🖥️ 监控系统快速启动指南

## 系统架构

```
┌─────────────────┐         ┌──────────────────┐         ┌───────────────┐
│  Trading Bot    │  ──────▶│  SQLite Database │◀──────  │  Web API      │
│  (main.py)      │  保存数据 │  (trading_data.db)│  读取数据 │(web_monitor.py)│
└─────────────────┘         └──────────────────┘         └───────┬───────┘
                                                                  │
                                                                  │ HTTP/REST
                                                                  │
                                                          ┌───────▼───────┐
                                                          │  Next.js UI   │
                                                          │ (localhost:3000)│
                                                          └───────────────┘
```

---

## 🚀 启动步骤

### 方式1：使用启动脚本（推荐）

```bash
cd /home/ling/Trade
./start_monitor.sh
```

### 方式2：分步启动

#### 第1步：启动后端API服务器

```bash
cd /home/ling/Trade
source venv/bin/activate
python web_monitor.py
```

期望输出：
```
================================================================================
🖥️  AI TRADING MONITOR STARTING
================================================================================

📊 Dashboard: http://localhost:8000
🔌 API Docs: http://localhost:8000/docs

================================================================================
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 第2步：启动前端Next.js应用

新开一个终端：

```bash
cd /home/ling/Trade/frontend
npm install  # 首次运行需要
npm run dev
```

期望输出：
```
   ▲ Next.js 14.2.0
   - Local:        http://localhost:3000

 ✓ Ready in 2.3s
```

#### 第3步：启动交易机器人（可选）

如果要看实时数据更新，再开一个终端运行交易bot：

```bash
cd /home/ling/Trade
source venv/bin/activate
python main.py
```

---

## 📊 访问监控界面

打开浏览器访问：

- **监控界面**: http://localhost:3000
- **API文档**: http://localhost:8000/docs
- **直接API测试**: http://localhost:8000/api/account

---

## 🔍 测试API接口

### 测试账户数据

```bash
curl http://localhost:8000/api/account
```

期望返回：
```json
{
  "id": 1,
  "timestamp": "2025-10-21 14:08:17",
  "total_value": 10000.0,
  "total_return": 0.0,
  "num_positions": 0,
  "available_balance": 10000.0,
  "used_balance": 0.0,
  "unrealized_pnl": 0.0
}
```

### 测试价格数据

```bash
curl http://localhost:8000/api/prices
```

### 测试AI决策

```bash
curl http://localhost:8000/api/decisions?limit=5
```

### 测试持仓

```bash
curl http://localhost:8000/api/positions
```

---

## 🎨 前端功能说明

### 1. 顶部价格栏
- 实时显示6个交易对当前价格
- 彩色圆点区分不同币种

### 2. 主图表区域
- 显示账户总价值历史曲线
- 切换ALL/72H时间范围
- 显示总收益率百分比

### 3. AI决策列表（DECISIONS标签）
显示最近20条AI交易决策，包括：
- 币种 + 方向（LONG/SHORT/HOLD）
- 入场价、止损价、止盈价
- 杠杆倍数
- 置信度
- AI推理过程

### 4. 持仓列表（POSITIONS标签）
显示当前所有活跃持仓，包括：
- 币种 + 方向标签
- 入场价/当前价
- 持仓数量
- 杠杆倍数
- 未实现盈亏（实时更新）
- 收益率百分比
- 开仓时间

---

## 🔄 数据流

```
1. Trading Bot 运行
   ↓
2. 每2.6分钟收集市场数据
   ↓
3. AI分析并生成决策
   ↓
4. 保存到SQLite数据库
   ↓
5. Web API从数据库读取
   ↓
6. Next.js前端每5秒刷新显示
```

---

## 🐛 故障排除

### 前端显示"Loading..."一直不消失

检查：
1. 后端API是否在运行？`curl http://localhost:8000/api/account`
2. 是否有CORS错误？打开浏览器开发者工具查看Console
3. 数据库是否有数据？`ls -lh trading_data.db`

### 图表显示"No data available"

这是正常的！因为刚启动时数据库是空的。

解决方案：
1. 运行交易bot (`python main.py`)
2. 等待至少一个交易周期（2.6分钟）
3. 刷新页面

### API返回空数组`[]`

说明数据库还没有数据，运行交易bot生成数据。

### 端口被占用

```bash
# 查看占用端口的进程
lsof -i :8000  # 后端
lsof -i :3000  # 前端

# 杀死进程
kill -9 <PID>
```

或者改用其他端口：

```bash
# 前端使用3001端口
cd frontend
npm run dev -- -p 3001

# 后端修改web_monitor.py最后一行
# uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
```

---

## 📝 数据库位置

SQLite数据库文件：`/home/ling/Trade/trading_data.db`

查看数据：
```bash
sqlite3 trading_data.db

# SQL查询示例
SELECT * FROM account_state ORDER BY timestamp DESC LIMIT 5;
SELECT * FROM coin_prices ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM ai_decisions ORDER BY timestamp DESC LIMIT 10;
SELECT * FROM positions WHERE active = 1;
```

---

## 🎯 完整测试流程

1. **启动所有服务**
   ```bash
   # Terminal 1: 后端API
   python web_monitor.py
   
   # Terminal 2: 前端UI
   cd frontend && npm run dev
   
   # Terminal 3: 交易Bot
   python main.py
   ```

2. **访问监控界面**
   - 打开 http://localhost:3000
   - 应该看到黑色背景的界面

3. **等待数据生成**
   - 交易bot会在2.6分钟后生成第一批数据
   - 前端会自动刷新显示

4. **检查各个功能**
   - ✓ 顶部价格栏显示6个币种价格
   - ✓ 主图表显示账户价值曲线
   - ✓ DECISIONS标签显示AI决策
   - ✓ POSITIONS标签显示持仓（如果有交易）

---

## 🎨 UI样式特点

- **黑白简约风格**
- 黑色背景 (#000000)
- 白色文字 (#ffffff)
- 绿色盈利 (#00ff00)
- 红色亏损 (#ff0000)
- 灰色次要信息 (#666666)
- 最小化视觉干扰
- 数据为中心的设计

---

## 📦 项目文件结构

```
/home/ling/Trade/
├── main.py                    # 交易bot主程序
├── web_monitor.py             # 后端API服务器
├── trading_data.db            # SQLite数据库
├── src/
│   ├── database/
│   │   └── models.py         # 数据库模型
│   └── ...
└── frontend/                  # Next.js前端
    ├── app/
    │   ├── page.tsx          # 主页面
    │   └── layout.tsx        # 布局
    ├── components/
    │   ├── PriceBar.tsx      # 价格栏组件
    │   ├── AccountChart.tsx  # 图表组件
    │   ├── DecisionsList.tsx # 决策列表
    │   └── PositionsList.tsx # 持仓列表
    └── lib/
        └── api.ts            # API调用函数
```

---

## ✅ 接口对应关系

| 前端调用 | 后端API | 数据库表 | 用途 |
|---------|---------|----------|------|
| `fetchAccount()` | `/api/account` | `account_state` | 账户状态 |
| `fetchPrices()` | `/api/prices` | `coin_prices` | 币种价格 |
| `fetchDecisions()` | `/api/decisions` | `ai_decisions` | AI决策 |
| `fetchPositions()` | `/api/positions` | `positions` | 持仓信息 |
| `fetchAccountHistory()` | `/api/account_history` | `account_state` | 历史数据 |

---

## 🎉 完成！

监控系统已完全配置好，享受实时监控你的AI交易！

