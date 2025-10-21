# 📚 文档索引

> 项目文档已精简，只保留核心必要文档

## 🎯 快速导航

### 新手必读（按顺序）

1. **[../CONTEXT.md](../CONTEXT.md)** ⭐ 
   - **最重要的文档！**
   - 项目完整上下文总览
   - 用于恢复对话上下文
   - 包含：架构、最近更新、快速启动、常见问题

2. **[../README.md](../README.md)**
   - 项目总体介绍
   - 快速开始指南
   - 功能特性列表

3. **[ARCHITECTURE.md](ARCHITECTURE.md)**
   - 详细的系统架构设计
   - 模块划分和职责
   - 数据流向

---

## 📖 进阶文档

### 交易逻辑

**[TRADING_LOGIC.md](TRADING_LOGIC.md)**
- nof1.ai 交易逻辑详解
- 失效条件机制
- 风险管理策略
- 仓位计算方法

### 监控系统

**[MONITOR_QUICKSTART.md](MONITOR_QUICKSTART.md)**
- Web监控界面快速启动
- Frontend + Backend 配置
- 常见问题排查

### AI 配置

**[THIRD_PARTY_API.md](THIRD_PARTY_API.md)**
- 第三方 AI API 使用指南
- SiliconFlow、OneAPI 等配置
- API密钥管理

**[REASONING_MODELS.md](REASONING_MODELS.md)**
- 推理模型支持
- DeepSeek-R1、o1-preview 等
- `<think>` 标签处理

---

## 🗂️ 文档结构

```
/home/ling/Trade/
├── CONTEXT.md              ⭐ 完整上下文（新对话必读）
├── README.md               📖 项目总览
│
└── docs/
    ├── README.md           📚 本文档索引
    │
    ├── ARCHITECTURE.md     🏗️ 架构设计
    ├── TRADING_LOGIC.md    📈 交易逻辑
    ├── MONITOR_QUICKSTART.md  🖥️ 监控快速启动
    ├── THIRD_PARTY_API.md  🔌 第三方API
    └── REASONING_MODELS.md 🧠 推理模型
```

---

## 🎓 学习路径建议

### Day 1：了解项目
1. 读 `CONTEXT.md` （15分钟）
2. 读 `README.md` （10分钟）
3. 运行 Paper Trading （30分钟）

### Day 2-3：深入理解
1. 读 `ARCHITECTURE.md` （30分钟）
2. 读 `TRADING_LOGIC.md` （30分钟）
3. 研究代码 `src/trading_bot.py` （1小时）

### Day 4-7：实践优化
1. 配置监控系统 （参考 `MONITOR_QUICKSTART.md`）
2. 测试第三方API （参考 `THIRD_PARTY_API.md`）
3. 调整配置参数
4. 分析交易数据

---

## ✅ 文档维护原则

1. **CONTEXT.md 是核心** - 所有重要信息都应该在这里
2. **避免重复** - 一个主题只在一个地方详细说明
3. **保持更新** - 重大更新后及时更新文档
4. **简洁明了** - 代码胜于千言

---

## 🔍 快速查找

**找不到想要的信息？**

| 你想了解... | 查看文档 |
|------------|---------|
| 项目是什么 | `CONTEXT.md` 或 `README.md` |
| 如何快速启动 | `CONTEXT.md` § 快速启动 |
| 系统架构 | `ARCHITECTURE.md` |
| 交易逻辑 | `TRADING_LOGIC.md` |
| 监控界面 | `MONITOR_QUICKSTART.md` |
| AI配置 | `THIRD_PARTY_API.md` |
| 推理模型 | `REASONING_MODELS.md` |
| 常见问题 | `CONTEXT.md` § 常见问题 |
| 最近更新 | `CONTEXT.md` § 最近重大更新 |

---

**提示：如果你是在新对话中恢复上下文，直接读 `CONTEXT.md` 即可！**

