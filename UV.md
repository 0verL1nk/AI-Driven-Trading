# UV Project Management Guide

## 什么是 UV？

`uv` 是由 Astral 开发的极速 Python 包管理器和项目管理工具，比传统的 pip 快 10-100 倍。

## 本地开发使用 UV

### 1. 安装 uv

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv
```

### 2. 创建虚拟环境

```bash
# 使用 uv 创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 使用 uv 安装依赖（比 pip 快很多）
uv pip install -r requirements.txt

# 或使用 pyproject.toml（推荐）
uv sync
```

### 4. 运行项目

```bash
# 安装依赖后
python main.py

# 或直接使用 uv run（自动管理环境）
uv run python main.py
```

## UV 常用命令

```bash
# 安装依赖
uv pip install <package>

# 安装开发依赖
uv pip install -e ".[dev]"

# 同步依赖（从 pyproject.toml）
uv sync

# 更新依赖
uv pip install --upgrade <package>

# 列出已安装包
uv pip list

# 导出依赖
uv pip compile requirements.txt -o requirements.lock
```

## Docker 构建

Dockerfile 已经配置使用 uv，构建速度会更快：

```bash
docker build -t ai-trading-bot .
```

## 优势

- **速度**: 比 pip 快 10-100 倍
- **兼容性**: 完全兼容 pip 和 requirements.txt
- **项目管理**: 支持 pyproject.toml
- **虚拟环境**: 自动管理，无需手动创建

## 迁移建议

1. 保留 `requirements.txt` 作为兼容
2. 使用 `pyproject.toml` 作为主要配置（更现代）
3. 本地开发使用 `uv sync` 或 `uv pip install`
4. Docker 构建自动使用 uv

