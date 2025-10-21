# 快速安装（解决依赖冲突）

## 🚨 如果遇到安装卡住

如果 `pip install -r requirements.txt` 卡在依赖解析，请按 `Ctrl+C` 中断，然后使用下面的方法。

## ✅ 方法1：使用固定版本（推荐）

```bash
# 中断当前安装
Ctrl+C

# 使用固定版本配置
pip install -r requirements-fixed.txt
```

## ✅ 方法2：最小安装（最快）

```bash
# 只安装核心依赖
pip install -r requirements-minimal.txt
```

## ✅ 方法3：手动安装（最稳定）

```bash
# 1. 核心依赖
pip install python-dotenv==1.0.0 pydantic==2.5.0 pydantic-settings==2.1.0

# 2. 数据和交易
pip install ccxt==4.2.10 pandas==2.1.4 numpy==1.26.2

# 3. 技术指标
pip install pandas-ta==0.3.14b0

# 4. AI
pip install openai==1.6.1

# 5. 工具
pip install aiohttp==3.9.1 requests==2.31.0 python-dateutil==2.8.2 pytz==2023.3
```

## 🔍 验证安装

```bash
python -c "import ccxt, pandas, numpy, openai; print('✅ 核心依赖安装成功')"
python test_system.py
```

## ❓ 关于TA-Lib

**不需要安装！** 系统已经使用 `pandas-ta` 作为替代，功能完全相同。

如果确实想要TA-Lib（更快但需要编译）：

```bash
# Ubuntu/Debian
sudo apt-get install ta-lib
pip install TA-Lib==0.4.28
```

## 🎯 推荐配置

**新手推荐**：使用 `requirements-minimal.txt`
- 最快安装
- 包含所有核心功能
- 避免可选依赖问题

**完整功能**：使用 `requirements-fixed.txt`  
- 固定版本，避免冲突
- 包含大部分功能
- 仍然排除了可选数据库等

**开发者**：手动安装
- 完全控制
- 按需添加依赖
- 最灵活

---

**遇到问题？参考 `INSTALL_GUIDE.md` 获取详细帮助。**

