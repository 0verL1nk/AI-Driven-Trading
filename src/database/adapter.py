"""
Database abstraction layer supporting SQLite and MySQL.
"""
import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import os

logger = logging.getLogger(__name__)


class DatabaseAdapter(ABC):
    """Abstract database adapter interface."""
    
    @abstractmethod
    def connect(self) -> Any:
        """Create and return database connection."""
        pass
    
    @abstractmethod
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results as list of dicts."""
        pass
    
    @abstractmethod
    def execute_write(self, query: str, params: tuple = None) -> None:
        """Execute INSERT/UPDATE/DELETE query."""
        pass
    
    @abstractmethod
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets."""
        pass
    
    @abstractmethod
    def init_database(self) -> None:
        """Initialize database schema."""
        pass
    
    @abstractmethod
    def quote(self, identifier: str) -> str:
        """Quote identifier for database-specific syntax."""
        pass
    
    @abstractmethod
    def get_last_insert_id(self, cursor: Any) -> int:
        """Get last insert ID."""
        pass


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter."""
    
    def __init__(self, db_path: str):
        import sqlite3
        self.db_path = db_path
        self.sqlite3 = sqlite3
    
    def connect(self):
        """Create SQLite connection."""
        conn = self.sqlite3.connect(self.db_path)
        conn.row_factory = self.sqlite3.Row
        return conn
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_write(self, query: str, params: tuple = None) -> None:
        """Execute write query."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
    
    def init_database(self) -> None:
        """Initialize SQLite schema."""
        with self.connect() as conn:
            cursor = conn.cursor()
            self._create_tables(cursor)
            
            # Check and add missing columns
            self._add_missing_columns(cursor)
            
            conn.commit()
            logger.info(f"SQLite database initialized at {self.db_path}")
    
    def quote(self, identifier: str) -> str:
        """SQLite doesn't need quoting for identifiers."""
        return identifier
    
    def get_last_insert_id(self, cursor: Any) -> int:
        """Get last insert ID."""
        return cursor.lastrowid
    
    def _create_tables(self, cursor):
        """Create all tables."""
        # Account state table
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
        
        # System config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Coin prices table
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
        
        # AI decisions table
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
        
        # Positions table
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
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                close_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                entry_timestamp DATETIME,
                symbol TEXT,
                side TEXT,
                quantity REAL,
                entry_price REAL,
                exit_price REAL,
                entry_notional REAL,
                exit_notional REAL,
                leverage INTEGER,
                pnl REAL,
                pnl_percent REAL,
                duration_minutes INTEGER,
                reason TEXT
            )
        """)
    
    def _add_missing_columns(self, cursor):
        """Add missing columns for backward compatibility."""
        # Check for thinking column
        cursor.execute("""
            SELECT COUNT(*) FROM pragma_table_info('ai_decisions') 
            WHERE name='thinking'
        """)
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE ai_decisions ADD COLUMN thinking TEXT")
            logger.info("Added 'thinking' column to ai_decisions table")
        
        # Check for new trade_history columns
        cursor.execute("SELECT COUNT(*) FROM pragma_table_info('trade_history') WHERE name='entry_timestamp'")
        if cursor.fetchone()[0] == 0:
            cursor.execute("ALTER TABLE trade_history ADD COLUMN entry_timestamp DATETIME")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN entry_notional REAL")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN exit_notional REAL")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN leverage INTEGER")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN reason TEXT")
            logger.info("Added new columns to trade_history table")


class MySQLAdapter(DatabaseAdapter):
    """MySQL database adapter."""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        try:
            import pymysql
            self.pymysql = pymysql
        except ImportError:
            raise ImportError("pymysql is required for MySQL support. Install with: pip install pymysql")
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
    
    def connect(self):
        """Create MySQL connection."""
        conn = self.pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            charset='utf8mb4',
            cursorclass=self.pymysql.cursors.DictCursor
        )
        return conn
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        finally:
            conn.close()
    
    def execute_write(self, query: str, params: tuple = None) -> None:
        """Execute write query."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                conn.commit()
        finally:
            conn.close()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute query with multiple parameter sets."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                cursor.executemany(query, params_list)
                conn.commit()
        finally:
            conn.close()
    
    def init_database(self) -> None:
        """Initialize MySQL schema."""
        conn = self.connect()
        try:
            with conn.cursor() as cursor:
                self._create_tables(cursor)
                self._add_missing_columns(cursor)
            conn.commit()
            logger.info(f"MySQL database initialized: {self.user}@{self.host}:{self.port}/{self.database}")
        finally:
            conn.close()
    
    def quote(self, identifier: str) -> str:
        """Quote MySQL identifier."""
        return f"`{identifier}`"
    
    def get_last_insert_id(self, cursor: Any) -> int:
        """Get last insert ID."""
        return cursor.lastrowid
    
    def _create_tables(self, cursor):
        """Create all tables."""
        # Account state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_state (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_value DOUBLE,
                total_return DOUBLE,
                num_positions INT,
                available_balance DOUBLE,
                used_balance DOUBLE,
                unrealized_pnl DOUBLE,
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # System config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                `key` VARCHAR(255) PRIMARY KEY,
                value TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Coin prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coin_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(50),
                price DOUBLE,
                rsi_14 DOUBLE,
                macd DOUBLE,
                funding_rate DOUBLE,
                open_interest DOUBLE,
                INDEX idx_symbol_timestamp (symbol, timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # AI decisions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_decisions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                coin VARCHAR(50),
                decision VARCHAR(50),
                side VARCHAR(10),
                confidence DOUBLE,
                leverage INT,
                entry_price DOUBLE,
                stop_loss DOUBLE,
                take_profit DOUBLE,
                risk_usd DOUBLE,
                reasoning TEXT,
                thinking TEXT,
                executed BOOLEAN DEFAULT 0,
                INDEX idx_timestamp (timestamp),
                INDEX idx_coin (coin)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                symbol VARCHAR(50),
                side VARCHAR(10),
                quantity DOUBLE,
                entry_price DOUBLE,
                current_price DOUBLE,
                leverage INT,
                unrealized_pnl DOUBLE,
                stop_loss DOUBLE,
                take_profit DOUBLE,
                active BOOLEAN DEFAULT 1,
                INDEX idx_active (active),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Trade history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                close_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                entry_timestamp DATETIME,
                symbol VARCHAR(50),
                side VARCHAR(10),
                quantity DOUBLE,
                entry_price DOUBLE,
                exit_price DOUBLE,
                entry_notional DOUBLE,
                exit_notional DOUBLE,
                leverage INT,
                pnl DOUBLE,
                pnl_percent DOUBLE,
                duration_minutes INT,
                reason VARCHAR(255),
                INDEX idx_close_timestamp (close_timestamp),
                INDEX idx_symbol (symbol)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
    
    def _add_missing_columns(self, cursor):
        """Add missing columns for backward compatibility."""
        # Check for thinking column
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'ai_decisions' 
            AND COLUMN_NAME = 'thinking'
        """, (self.database,))
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.execute("ALTER TABLE ai_decisions ADD COLUMN thinking TEXT")
            logger.info("Added 'thinking' column to ai_decisions table")
        
        # Check for new trade_history columns
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'trade_history' 
            AND COLUMN_NAME = 'entry_timestamp'
        """, (self.database,))
        if cursor.fetchone()['COUNT(*)'] == 0:
            cursor.execute("ALTER TABLE trade_history ADD COLUMN entry_timestamp DATETIME")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN entry_notional DOUBLE")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN exit_notional DOUBLE")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN leverage INT")
            cursor.execute("ALTER TABLE trade_history ADD COLUMN reason VARCHAR(255)")
            logger.info("Added new columns to trade_history table")


def create_database_adapter(db_type: str = "sqlite", **kwargs) -> DatabaseAdapter:
    """
    Factory function to create database adapter.
    
    Args:
        db_type: 'sqlite' or 'mysql'
        **kwargs: Database-specific parameters
            - For SQLite: db_path (default: "trading_data.db")
            - For MySQL: host, port, user, password, database
    
    Returns:
        DatabaseAdapter instance
    """
    if db_type.lower() == "sqlite":
        db_path = kwargs.get("db_path", "trading_data.db")
        return SQLiteAdapter(db_path)
    
    elif db_type.lower() == "mysql":
        required = ["host", "user", "password", "database"]
        missing = [k for k in required if k not in kwargs]
        if missing:
            raise ValueError(f"Missing required MySQL parameters: {', '.join(missing)}")
        
        host = kwargs["host"]
        port = kwargs.get("port", 3306)
        user = kwargs["user"]
        password = kwargs["password"]
        database = kwargs["database"]
        
        return MySQLAdapter(host, port, user, password, database)
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}. Use 'sqlite' or 'mysql'")

