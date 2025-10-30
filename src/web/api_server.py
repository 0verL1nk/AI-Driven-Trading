"""
Web API Server for Trading Monitor
Provides HTTP endpoints for monitoring trading bot status and data.
"""

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..database import TradingDatabase

logger = logging.getLogger(__name__)


class WebAPIServer:
    """Web API server for monitoring trading bot."""
    
    def __init__(self, db: TradingDatabase, port: int = 8541, running_callback=None):
        """
        Initialize Web API server.
        
        Args:
            db: TradingDatabase instance for data access
            port: Port number for the web server
            running_callback: Callable that returns running status (for WebSocket)
        """
        self.db = db
        self.port = port
        self.running_callback = running_callback or (lambda: True)
        self.app: Optional[FastAPI] = None
        self.server_task: Optional[asyncio.Task] = None
        self.running = False
    
    def create_app(self) -> FastAPI:
        """Create and configure FastAPI application."""
        app = FastAPI(title="AI Trading Monitor")
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Mount static files
        static_dir = Path(__file__).parent.parent.parent.parent / "static"
        static_dir.mkdir(exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register API routes."""
        
        @app.get("/")
        async def read_root():
            """Return homepage."""
            static_dir = Path(__file__).parent.parent.parent.parent / "static"
            html_file = static_dir / "index.html"
            if html_file.exists():
                return FileResponse(html_file)
            return {"message": "AI Trading Monitor API"}
        
        @app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring and container orchestration."""
            account = None
            try:
                # Check database connection
                account = self.db.get_latest_account_state()
                db_status = "healthy"
            except Exception as e:
                logger.error(f"Database health check failed: {e}")
                db_status = "unhealthy"
            
            # Get bot running status (always True when running separately)
            bot_running = self.running_callback() if callable(self.running_callback) else True
            
            return {
                "status": "healthy" if db_status == "healthy" else "degraded",
                "service": "ai-trading-bot-web-server",
                "database": db_status,
                "bot_running": bot_running if callable(self.running_callback) else None,  # None means separate process
                "timestamp": account.get("timestamp") if account else None
            }
        
        @app.get("/api/health")
        async def api_health_check():
            """API health check endpoint (alias for /health)."""
            return await health_check()
        
        @app.get("/api/account")
        async def get_account():
            """Get account status."""
            account = self.db.get_latest_account_state()
            return account or {"total_value": 0, "total_return": 0, "num_positions": 0}
        
        @app.get("/api/prices")
        async def get_prices():
            """Get latest prices."""
            prices = self.db.get_latest_prices()
            return prices
        
        @app.get("/api/decisions")
        async def get_decisions(limit: int = 20):
            """Get AI decision history."""
            # Input validation
            if limit < 1 or limit > 1000:
                limit = 20
            decisions = self.db.get_recent_decisions(limit)
            return decisions
        
        @app.get("/api/positions")
        async def get_positions():
            """Get current positions."""
            positions = self.db.get_active_positions()
            return positions
        
        @app.get("/api/account_history")
        async def get_account_history(
            hours: int = 24, 
            mode: str = 'auto',
            since: str = None
        ):
            """
            Get account history data with smart sampling.
            
            Args:
                hours: Number of hours to query (default: 24)
                mode: Sampling mode ('full', 'auto', 'fast')
                since: ISO timestamp for incremental query (optional)
            """
            # Input validation
            if mode not in ['full', 'auto', 'fast']:
                mode = 'auto'
            
            if hours < 1 or hours > 720:
                hours = 24
            
            if since:
                # Incremental query
                history = self.db.get_account_history_since(since)
                return {
                    "data": history,
                    "count": len(history),
                    "mode": "incremental",
                    "since": since
                }
            else:
                # Full query
                history = self.db.get_account_history(hours, mode)
                return {
                    "data": history,
                    "count": len(history),
                    "mode": mode,
                    "hours": hours
                }
        
        @app.get("/api/price_history/{symbol}")
        async def get_price_history(symbol: str, hours: int = 24):
            """Get price history for a symbol."""
            # Input validation
            if not re.match(r'^[A-Z0-9]+(/[A-Z0-9]+)*(:[A-Z0-9]+)?$', symbol):
                return {"error": "Invalid symbol format"}
            
            if hours < 1 or hours > 720:
                hours = 24
            
            history = self.db.get_price_history(symbol, hours)
            return history
        
        @app.get("/api/trades")
        async def get_trades(page: int = 1, page_size: int = 10):
            """
            Get trade history with pagination.
            
            Args:
                page: Page number (starts from 1)
                page_size: Number of records per page
            """
            # Input validation
            if page < 1:
                page = 1
            if page_size < 1 or page_size > 100:
                page_size = 10
            
            offset = (page - 1) * page_size
            
            total = self.db.get_trades_count()
            trades = self.db.get_trade_history_paginated(offset, page_size)
            
            return {
                "data": trades,
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket endpoint for real-time updates."""
            await websocket.accept()
            try:
                while self.running:
                    # Push latest data every 3 seconds
                    data = {
                        "account": self.db.get_latest_account_state(),
                        "prices": self.db.get_latest_prices(),
                        "positions": self.db.get_active_positions()
                    }
                    await websocket.send_json(data)
                    await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                await websocket.close()
    
    async def start(self):
        """Start the web server."""
        if self.app is None:
            self.app = self.create_app()
        
        self.running = True
        
        logger.info(f"🌐 Starting Web Monitor API on port {self.port}")
        logger.info(f"   Dashboard: http://localhost:{self.port}")
        logger.info(f"   API Docs: http://localhost:{self.port}/docs")
        
        config = uvicorn.Config(
            app=self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info",
            access_log=False  # Reduce log noise
        )
        server = uvicorn.Server(config)
        try:
            await server.serve()
        except asyncio.CancelledError:
            logger.info("🌐 Web server cancelled")
            raise
        finally:
            self.running = False
    
    async def stop(self):
        """Stop the web server."""
        logger.info("🛑 Stopping Web API server...")
        self.running = False
        if self.server_task and not self.server_task.done():
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Web API server stopped")

