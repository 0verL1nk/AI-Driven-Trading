# 安装指南

## 🚀 快速安装

### 步骤1：创建虚拟环境

```bash
cd /home/ling/Trade
python3 -m venv venv
source venv/bin/activate
```

### 步骤2：安装依赖

```bash
pip install -r requirements.txt
```

## ⚠️ 常见问题

### 问题1：numpy版本冲突

**错误信息：**
```
ERROR: Cannot install numpy==1.26.2 and pandas-ta because these package versions have conflicting dependencies.
```

**解决方案：**
```bash
# 修改requirements.txt中的numpy版本
numpy>=1.26.0,<2.0.0
pandas-ta>=0.3.14b  # 不固定版本
```

### 问题2：TA-Lib安装失败

**错误信息：**
```
error: command 'gcc' failed
```

**原因：**
TA-Lib是C库，需要先安装系统依赖。

**解决方案A：安装TA-Lib C库（推荐）**

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# 然后安装Python包
pip install TA-Lib
```

**解决方案B：不安装TA-Lib（简单）**

在`requirements.txt`中注释掉TA-Lib：

```txt
# TA-Lib>=0.4.28  # 注释掉
pandas-ta>=0.3.14b  # 使用pandas-ta替代
```

系统会自动检测并降级到pandas-ta。

### 问题3：依赖版本冲突

**通用解决方案：**

```bash
# 清理环境
pip cache purge
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# 使用宽松版本安装
pip install --upgrade pip
pip install -r requirements.txt
```

## 📦 分步安装（推荐）

如果一次性安装失败，可以分步安装：

### 1. 核心依赖

```bash
pip install python-dotenv pydantic pydantic-settings
```

### 2. 交易所API

```bash
pip install ccxt pandas numpy
```

### 3. AI模型

```bash
pip install openai anthropic
```

### 4. 技术指标（可选）

```bash
# 选项A：使用pandas-ta（简单）
pip install pandas-ta

# 选项B：使用TA-Lib（需要C库）
# 先安装系统库（见上面），然后：
pip install TA-Lib
```

### 5. 其他依赖

```bash
pip install aiohttp requests python-dateutil pytz
pip install fastapi uvicorn websockets
```

## 🔍 验证安装

```bash
# 测试导入
python -c "import ccxt, pandas, numpy; print('Core libraries OK')"
python -c "import openai; print('OpenAI OK')"

# 测试pandas-ta
python -c "import pandas_ta; print('pandas-ta OK')"

# 测试TA-Lib（如果安装了）
python -c "import talib; print('TA-Lib OK')"

# 运行系统测试
python test_system.py
```

## 💡 最小安装（快速开始）

如果只想快速测试系统，可以只安装核心依赖：

```bash
pip install python-dotenv pydantic pydantic-settings
pip install ccxt pandas numpy pandas-ta
pip install openai
pip install aiohttp requests python-dateutil pytz
```

然后注释掉`requirements.txt`中的其他依赖。

## 🐳 使用Docker（避免依赖问题）

```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 🖥️ 不同系统安装

### Ubuntu/Debian

```bash
# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv build-essential

# 安装TA-Lib（可选）
sudo apt-get install -y ta-lib

# 安装Python依赖
pip install -r requirements.txt
```

### macOS

```bash
# 安装Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装TA-Lib
brew install ta-lib

# 安装Python依赖
pip install -r requirements.txt
```

### Windows (WSL推荐)

建议在WSL2中安装，参考Ubuntu安装步骤。

或使用Windows Subsystem for Linux:

```powershell
# 安装WSL2
wsl --install

# 然后在WSL中按Ubuntu步骤安装
```

## ✅ 安装成功检查

运行以下命令确认安装成功：

```bash
python scripts/check_config.py
python test_system.py
```

如果看到"All tests passed!"，说明安装成功！

## 🆘 仍然有问题？

1. 检查Python版本：
   ```bash
   python --version  # 应该是3.10+
   ```

2. 更新pip：
   ```bash
   pip install --upgrade pip
   ```

3. 使用国内镜像（如果网络慢）：
   ```bash
   pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
   ```

4. 查看详细错误：
   ```bash
   pip install -r requirements.txt -v
   ```

