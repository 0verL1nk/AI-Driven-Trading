"""
Web监控服务器 - 提供实时交易数据的Web界面
"""
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
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
    decisions = db.get_recent_decisions(limit)
    return decisions


@app.get("/api/positions")
async def get_positions():
    """获取当前持仓"""
    positions = db.get_active_positions()
    return positions


@app.get("/api/account_history")
async def get_account_history(hours: int = 24):
    """获取账户历史数据"""
    history = db.get_account_history(hours)
    return history


@app.get("/api/price_history/{symbol}")
async def get_price_history(symbol: str, hours: int = 24):
    """获取价格历史"""
    history = db.get_price_history(symbol, hours)
    return history


@app.get("/api/trades")
async def get_trades(limit: int = 50):
    """获取交易历史"""
    trades = db.get_trade_history(limit)
    return trades


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

