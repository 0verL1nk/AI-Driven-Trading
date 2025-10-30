# Docker Deployment Guide

## Health Check

系统提供了健康检查端点用于监控服务状态：

**端点**: `GET /health` 或 `GET /api/health`

**响应示例**:
```json
{
  "status": "healthy",
  "service": "ai-trading-bot",
  "database": "healthy",
  "bot_running": true,
  "timestamp": "2025-10-30T12:34:56"
}
```

**使用方法**:
```bash
# 检查容器健康状态
curl http://localhost:8541/health

# 查看 Docker 健康检查状态
docker ps
docker inspect <container_id> | grep -A 10 Health
```

## Quick Start

### 1. Build Docker Image

```bash
docker build -t ai-trading-bot .
```

### 2. Run with Docker

```bash
# Using SQLite (default)
docker run -d \
  --name trading-bot \
  -p 8541:8541 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/trading_data.db:/app/trading_data.db \
  -v $(pwd)/config:/app/config \
  -e OPENAI_API_KEY=your_api_key \
  -e OPENAI_BASE_URL=https://api.siliconflow.cn/v1 \
  -e ENABLE_PAPER_TRADING=true \
  ai-trading-bot

# Using MySQL
docker run -d \
  --name trading-bot \
  -p 8541:8541 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config \
  -e DB_TYPE=mysql \
  -e DB_HOST=your_mysql_host \
  -e DB_PORT=3306 \
  -e DB_USER=your_user \
  -e DB_PASSWORD=your_password \
  -e DB_NAME=trading_db \
  -e OPENAI_API_KEY=your_api_key \
  -e OPENAI_BASE_URL=https://api.siliconflow.cn/v1 \
  ai-trading-bot
```

### 3. Run with Docker Compose

```bash
# Create .env file first
cp env.template .env
# Edit .env with your configuration

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_BASE_URL`: API base URL (optional, defaults to official OpenAI)

Optional:
- `DB_TYPE`: Database type (`sqlite` or `mysql`, default: `sqlite`)
- `DB_PATH`: SQLite database path (default: `trading_data.db`)
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: MySQL configuration
- `ENABLE_PAPER_TRADING`: Enable paper trading (`true` or `false`, default: `true`)
- `USE_TESTNET`: Use Binance testnet (`true` or `false`, default: `false`)
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`: Exchange API keys (optional)

## Access

- Web API: http://localhost:8541
- API Docs: http://localhost:8541/docs

## Health Check

The container includes a health check that monitors the `/api/account` endpoint.

## Logs

```bash
# View logs
docker logs -f trading-bot

# Or with docker-compose
docker-compose logs -f
```

## Troubleshooting

1. **Container exits immediately**: Check logs with `docker logs trading-bot`
2. **Database connection errors**: Verify database credentials and network connectivity
3. **API errors**: Check `OPENAI_API_KEY` and `OPENAI_BASE_URL` environment variables

