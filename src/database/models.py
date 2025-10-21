"""
SQLite Database Models for Trading Bot
存储账户状态、价格数据、AI决策等
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class TradingDatabase:
    """Trading bot数据库管理器"""
    
    def __init__(self, db_path: str = "trading_data.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 账户状态表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS account_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_value REAL,
                    total_return REAL,
                    num_positions INTEGER,
                    available_balance REAL,
                    used_balance REAL,
                    unrealized_pnl REAL
                )
            """)
            
            # 币种价格表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS coin_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    price REAL,
                    rsi_14 REAL,
                    macd REAL,
                    funding_rate REAL,
                    open_interest REAL
                )
            """)
            
            # AI决策表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    coin TEXT,
                    decision TEXT,
                    side TEXT,
                    confidence REAL,
                    leverage INTEGER,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    risk_usd REAL,
                    reasoning TEXT,
                    thinking TEXT,
                    executed BOOLEAN DEFAULT 0
                )
            """)
            
            # Add thinking column if it doesn't exist (for existing databases)
            cursor.execute("""
                SELECT COUNT(*) FROM pragma_table_info('ai_decisions') 
                WHERE name='thinking'
            """)
            if cursor.fetchone()[0] == 0:
                cursor.execute("ALTER TABLE ai_decisions ADD COLUMN thinking TEXT")
                logger.info("Added 'thinking' column to ai_decisions table")
            
            # 持仓表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    quantity REAL,
                    entry_price REAL,
                    current_price REAL,
                    leverage INTEGER,
                    unrealized_pnl REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    active BOOLEAN DEFAULT 1
                )
            """)
            
            # 交易历史表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT,
                    side TEXT,
                    quantity REAL,
                    entry_price REAL,
                    exit_price REAL,
                    pnl REAL,
                    pnl_percent REAL,
                    duration_minutes INTEGER
                )
            """)
            
            conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
    
    def save_account_state(self, state: Dict):
        """保存账户状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO account_state 
                (total_value, total_return, num_positions, available_balance, 
                 used_balance, unrealized_pnl)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state.get('total_value', 0),
                state.get('total_return', 0),
                state.get('num_positions', 0),
                state.get('available_balance', 0),
                state.get('used_balance', 0),
                state.get('unrealized_pnl', 0)
            ))
            conn.commit()
    
    def save_coin_price(self, symbol: str, price_data: Dict):
        """保存币种价格数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO coin_prices 
                (symbol, price, rsi_14, macd, funding_rate, open_interest)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                symbol,
                price_data.get('price', 0),
                price_data.get('rsi_14', 0),
                price_data.get('macd', 0),
                price_data.get('funding_rate', 0),
                price_data.get('open_interest', 0)
            ))
            conn.commit()
    
    def save_ai_decision(self, coin: str, decision: Dict, thinking: str = ""):
        """保存AI决策"""
        # Validate decision is a dict
        if not isinstance(decision, dict):
            logger.warning(f"save_ai_decision: decision for {coin} is not a dict, got {type(decision)}")
            return
        
        # Extract trade_signal_args if present
        args = decision.get('trade_signal_args', {})
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_decisions 
                (coin, decision, side, confidence, leverage, entry_price, 
                 stop_loss, take_profit, risk_usd, reasoning, thinking, executed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                coin,
                args.get('signal', 'hold') if args else decision.get('decision', 'hold'),
                decision.get('side', ''),
                args.get('confidence', 0) if args else decision.get('confidence', 0),
                args.get('leverage', 0) if args else decision.get('leverage', 0),
                args.get('entry_price', 0) if args else decision.get('entry_price', 0),
                args.get('stop_loss', 0) if args else decision.get('stop_loss', 0),
                # 支持多种字段名
                (args.get('take_profit') or args.get('profit_target', 0)) if args else (decision.get('take_profit') or decision.get('profit_target', 0)),
                args.get('risk_usd', 0) if args else decision.get('risk_usd', 0),
                decision.get('reasoning', ''),
                thinking,  # AI思考过程
                decision.get('executed', False)
            ))
            conn.commit()
    
    def save_position(self, position: Dict):
        """保存持仓信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO positions 
                (symbol, side, quantity, entry_price, current_price, leverage,
                 unrealized_pnl, stop_loss, take_profit, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.get('symbol', ''),
                position.get('side', ''),
                position.get('quantity', 0),
                position.get('entry_price', 0),
                position.get('current_price', 0),
                position.get('leverage', 0),
                position.get('unrealized_pnl', 0),
                position.get('stop_loss', 0),
                position.get('take_profit', 0),
                position.get('active', True)
            ))
            conn.commit()
    
    def get_latest_account_state(self) -> Optional[Dict]:
        """获取最新账户状态"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM account_state 
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_latest_prices(self) -> List[Dict]:
        """获取最新价格（每个币种最新一条）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT cp1.* FROM coin_prices cp1
                INNER JOIN (
                    SELECT symbol, MAX(timestamp) as max_time
                    FROM coin_prices
                    GROUP BY symbol
                ) cp2 ON cp1.symbol = cp2.symbol 
                     AND cp1.timestamp = cp2.max_time
                ORDER BY cp1.symbol
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        """获取最近的AI决策"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ai_decisions 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_positions(self) -> List[Dict]:
        """获取活跃持仓"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM positions 
                WHERE active = 1
                ORDER BY timestamp DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_account_history(self, hours: int = 24) -> List[Dict]:
        """获取账户历史（用于图表）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM account_state 
                WHERE timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp ASC
            """, (hours,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """获取价格历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM coin_prices 
                WHERE symbol = ? 
                  AND timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp ASC
            """, (symbol, hours))
            return [dict(row) for row in cursor.fetchall()]

