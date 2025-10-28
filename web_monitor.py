"""
Web监控服务器 - 提供实时交易数据的Web界面
"""
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import re
from pathlib import Path
from src.database import TradingDatabase
import json
import asyncio

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Trading Monitor")

# 添加CORS中间件，允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Next.js前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = TradingDatabase()

# 挂载静态文件
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def read_root():
    """返回主页"""
    html_file = Path(__file__).parent / "static" / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return {"message": "AI Trading Monitor API"}


@app.get("/api/account")
async def get_account():
    """获取账户状态"""
    account = db.get_latest_account_state()
    return account or {"total_value": 0, "total_return": 0, "num_positions": 0}


@app.get("/api/prices")
async def get_prices():
    """获取最新价格"""
    prices = db.get_latest_prices()
    return prices


@app.get("/api/decisions")
async def get_decisions(limit: int = 20):
    """获取AI决策历史"""
    # 输入验证：limit参数
    if limit < 1 or limit > 1000:
        limit = 20
    
    decisions = db.get_recent_decisions(limit)
    return decisions


@app.get("/api/positions")
async def get_positions():
    """获取当前持仓"""
    positions = db.get_active_positions()
    return positions


@app.get("/api/account_history")
async def get_account_history(
    hours: int = 24, 
    mode: str = 'auto',
    since: str = None  # 增量查询：返回此时间戳之后的数据
):
    """
    获取账户历史数据 - 智能采样保持曲线完整性
    
    Args:
        hours: 查询最近多少小时的数据，默认24小时
        mode: 采样模式
            - 'full': 返回全部数据（完整曲线，可能很大）
            - 'auto': 智能采样，平衡性能和曲线完整性（推荐）
            - 'fast': 快速模式，最多200个点
        since: 增量查询，ISO格式时间戳（可选）
            - 如果提供，只返回此时间之后的新数据
            - 用于前端增量更新，减少数据传输
    """
    # 输入验证：mode参数
    if mode not in ['full', 'auto', 'fast']:
        mode = 'auto'  # 默认使用auto模式
    
    # 输入验证：hours参数
    if hours < 1 or hours > 720:  # 最多30天
        hours = 24
    
    if since:
        # 增量查询：只返回since之后的新数据
        history = db.get_account_history_since(since)
        return {
            "data": history,
            "count": len(history),
            "mode": "incremental",
            "since": since
        }
    else:
        # 全量查询
        history = db.get_account_history(hours, mode)
        return {
            "data": history,
            "count": len(history),
            "mode": mode,
            "hours": hours
        }


@app.get("/api/price_history/{symbol}")
async def get_price_history(symbol: str, hours: int = 24):
    """获取价格历史"""
    # 输入验证：symbol参数（只允许字母、数字和特定符号）
    if not re.match(r'^[A-Z0-9]+(/[A-Z0-9]+)*(:[A-Z0-9]+)?$', symbol):
        return {"error": "Invalid symbol format"}
    
    # 输入验证：hours参数
    if hours < 1 or hours > 720:
        hours = 24
    
    history = db.get_price_history(symbol, hours)
    return history


@app.get("/api/trades")
async def get_trades(page: int = 1, page_size: int = 10):
    """
    获取交易历史（分页）
    
    Args:
        page: 页码（从1开始）
        page_size: 每页记录数
    """
    # 输入验证
    if page < 1:
        page = 1
    if page_size < 1 or page_size > 100:
        page_size = 10
    
    # 计算offset
    offset = (page - 1) * page_size
    
    # 获取总数和数据
    total = db.get_trades_count()
    trades = db.get_trade_history_paginated(offset, page_size)
    
    return {
        "data": trades,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket实时推送"""
    await websocket.accept()
    try:
        while True:
            # 每3秒推送最新数据
            data = {
                "account": db.get_latest_account_state(),
                "prices": db.get_latest_prices(),
                "positions": db.get_active_positions()
            }
            await websocket.send_json(data)
            await asyncio.sleep(3)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    print("=" * 80)
    print("🖥️  AI TRADING MONITOR STARTING")
    print("=" * 80)
    print()
    print("📊 Dashboard: http://localhost:8541")
    print("🔌 API Docs: http://localhost:8541/docs")
    print()
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8541, log_level="info")

