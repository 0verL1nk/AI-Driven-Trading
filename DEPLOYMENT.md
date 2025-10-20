# 部署指南

## 🚀 生产环境部署

### 系统要求

- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / macOS
- **Python**: 3.10+
- **内存**: 最少2GB，推荐4GB+
- **存储**: 10GB+（用于日志和数据存储）
- **网络**: 稳定的互联网连接

### 部署步骤

#### 1. 服务器准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装依赖
sudo apt install -y python3.10 python3-pip python3-venv git

# 安装TA-Lib
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
```

#### 2. 克隆项目

```bash
cd /opt
git clone <your-repo-url> trading-bot
cd trading-bot
```

#### 3. 配置环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env  # 填入真实的API密钥
```

#### 4. 配置系统服务（Systemd）

创建 `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=AI Trading Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/opt/trading-bot
Environment="PATH=/opt/trading-bot/venv/bin"
ExecStart=/opt/trading-bot/venv/bin/python main.py
Restart=always
RestartSec=10

# 日志
StandardOutput=append:/var/log/trading-bot/stdout.log
StandardError=append:/var/log/trading-bot/stderr.log

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

创建日志目录：

```bash
sudo mkdir -p /var/log/trading-bot
sudo chown your-username:your-username /var/log/trading-bot
```

启动服务：

```bash
# 重载systemd
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable trading-bot

# 启动服务
sudo systemctl start trading-bot

# 查看状态
sudo systemctl status trading-bot

# 查看日志
sudo journalctl -u trading-bot -f
```

#### 5. 配置日志轮转

创建 `/etc/logrotate.d/trading-bot`:

```
/var/log/trading-bot/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 your-username your-username
    sharedscripts
    postrotate
        systemctl reload trading-bot > /dev/null 2>&1 || true
    endscript
}
```

### 使用Docker部署（推荐）

#### 1. 创建 Dockerfile

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建日志目录
RUN mkdir -p logs

# 运行
CMD ["python", "main.py"]
```

#### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  trading-bot:
    build: .
    container_name: ai-trading-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    networks:
      - trading-net
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  trading-net:
    driver: bridge
```

#### 3. 启动容器

```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止
docker-compose down
```

## 📊 监控和告警

### 1. 健康检查脚本

创建 `scripts/health_check.sh`:

```bash
#!/bin/bash

LOG_FILE="/var/log/trading-bot/stdout.log"
MAX_AGE=600  # 10分钟

# 检查进程是否运行
if ! systemctl is-active --quiet trading-bot; then
    echo "ERROR: Trading bot service is not running!"
    exit 1
fi

# 检查日志是否有最近更新
if [ -f "$LOG_FILE" ]; then
    LAST_MOD=$(stat -c %Y "$LOG_FILE")
    NOW=$(date +%s)
    AGE=$((NOW - LAST_MOD))
    
    if [ $AGE -gt $MAX_AGE ]; then
        echo "WARNING: Log file not updated for $AGE seconds"
        exit 1
    fi
fi

echo "OK: Trading bot is healthy"
exit 0
```

### 2. Cron定时检查

```bash
# 编辑crontab
crontab -e

# 添加每5分钟检查一次
*/5 * * * * /opt/trading-bot/scripts/health_check.sh || systemctl restart trading-bot
```

### 3. Telegram告警（可选）

在 `.env` 中配置：

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

系统会在以下情况发送告警：
- 开仓/平仓
- 触发止损/止盈
- 回撤超过阈值
- 系统错误

## 🔐 安全最佳实践

### 1. API密钥安全

```bash
# 限制.env文件权限
chmod 600 .env

# 不要提交.env到Git
echo ".env" >> .gitignore
```

### 2. 防火墙配置

```bash
# 只允许必要的出站连接
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

### 3. 定期备份

```bash
# 备份配置
tar -czf backup-$(date +%Y%m%d).tar.gz config/ .env

# 自动备份脚本（每天）
0 2 * * * cd /opt/trading-bot && tar -czf /backup/trading-bot-$(date +\%Y\%m\%d).tar.gz config/ .env
```

## 📈 性能优化

### 1. 使用Redis缓存

```python
# 安装Redis
sudo apt install redis-server

# 启动Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2. 数据库优化

```python
# 使用PostgreSQL存储历史数据
sudo apt install postgresql

# 创建数据库
sudo -u postgres psql
CREATE DATABASE trading_db;
CREATE USER trading_user WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE trading_db TO trading_user;
```

### 3. 日志级别调整

生产环境建议使用 `WARNING` 级别：

```yaml
# config/trading_config.yaml
logging:
  level: "WARNING"  # 减少日志量
```

## 🔄 更新和维护

### 更新系统

```bash
# 停止服务
sudo systemctl stop trading-bot

# 拉取更新
git pull

# 更新依赖
source venv/bin/activate
pip install -r requirements.txt --upgrade

# 重启服务
sudo systemctl start trading-bot
```

### 回滚版本

```bash
# 查看历史版本
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>

# 重启服务
sudo systemctl restart trading-bot
```

## ⚠️ 故障排查

### 常见问题

1. **服务无法启动**
   ```bash
   # 查看详细日志
   sudo journalctl -u trading-bot -n 100 --no-pager
   ```

2. **API调用失败**
   ```bash
   # 检查网络连接
   ping api.binance.com
   
   # 检查API密钥
   python scripts/check_config.py
   ```

3. **内存不足**
   ```bash
   # 监控内存使用
   free -h
   
   # 调整配置减少内存占用
   # 减少数据缓存大小
   ```

## 📞 技术支持

遇到问题？
1. 查看日志：`tail -f logs/trading.log`
2. 运行测试：`python test_system.py`
3. 检查配置：`python scripts/check_config.py`

