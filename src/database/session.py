"""
Database session management using SQLAlchemy
"""
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import logging
from typing import Optional

from .orm_models import Base

logger = logging.getLogger(__name__)


def create_database_url(db_type: str, **kwargs) -> str:
    """
    Create database URL for SQLAlchemy.
    
    Args:
        db_type: 'sqlite' or 'mysql'
        **kwargs: Database-specific parameters
            - For SQLite: db_path (default: "trading_data.db")
            - For MySQL: host, port, user, password, database, ssl_mode, ssl_ca
    
    Returns:
        Database URL string
    """
    if db_type.lower() == "sqlite":
        db_path = kwargs.get("db_path", "trading_data.db")
        return f"sqlite:///{db_path}"
    
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
        
        # Build connection string (SSL parameters are passed via connect_args, not URL)
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}?charset=utf8mb4"
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}. Use 'sqlite' or 'mysql'")


class DatabaseManager:
    """Database session manager"""
    
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """
        Initialize database manager.
        
        Args:
            db_type: 'sqlite' or 'mysql'
            **kwargs: Database-specific parameters
        """
        self.db_type = db_type.lower()
        self.db_url = create_database_url(db_type, **kwargs)
        
        # Create engine with appropriate settings
        if db_type == "sqlite":
            self.engine = create_engine(
                self.db_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
        else:  # MySQL
            # Prepare SSL connection arguments for pymysql
            connect_args = {}
            
            # Get SSL configuration from kwargs
            ssl_mode = kwargs.get("ssl_mode", "REQUIRED")
            ssl_ca = kwargs.get("ssl_ca")
            
            if ssl_mode != "DISABLED":
                # Enable SSL for pymysql
                # pymysql expects ssl dictionary with specific keys
                ssl_config = {}
                
                if ssl_ca:
                    # Use custom CA certificate
                    ssl_config["ca"] = ssl_ca
                    ssl_config["check_hostname"] = False
                else:
                    # Use system default CA certificates
                    # For TiDB Cloud and most cloud MySQL providers
                    # An empty dict or {'check_hostname': False} enables SSL with system CA
                    ssl_config["check_hostname"] = False
                
                # Only set ssl if we have a valid config
                if ssl_config:
                    connect_args["ssl"] = ssl_config
                    
            self.engine = create_engine(
                self.db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                connect_args=connect_args if connect_args else {},
                echo=False
            )
        
        # Create session factory
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize database schema
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info(f"Database initialized: {self.db_type} at {self.db_url.split('@')[-1] if '@' in self.db_url else self.db_url}")
            
            # Check and add missing columns for backward compatibility
            self._add_missing_columns()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _add_missing_columns(self):
        """Add missing columns for backward compatibility"""
        inspector = inspect(self.engine)
        
        # Check for thinking column in ai_decisions
        if 'ai_decisions' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('ai_decisions')]
            if 'thinking' not in columns:
                try:
                    with self.engine.connect() as conn:
                        if self.db_type == 'sqlite':
                            conn.execute("ALTER TABLE ai_decisions ADD COLUMN thinking TEXT")
                        else:  # MySQL
                            conn.execute("ALTER TABLE ai_decisions ADD COLUMN thinking TEXT")
                        conn.commit()
                    logger.info("Added 'thinking' column to ai_decisions table")
                except Exception as e:
                    logger.debug(f"Error adding thinking column (may already exist): {e}")
        
        # Check for new trade_history columns
        if 'trade_history' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('trade_history')]
            missing = ['entry_timestamp', 'entry_notional', 'exit_notional', 'leverage', 'reason']
            need_add = [col for col in missing if col not in columns]
            
            if need_add:
                try:
                    with self.engine.connect() as conn:
                        for col in need_add:
                            if col == 'entry_timestamp':
                                conn.execute("ALTER TABLE trade_history ADD COLUMN entry_timestamp DATETIME")
                            elif col in ['entry_notional', 'exit_notional']:
                                conn.execute(f"ALTER TABLE trade_history ADD COLUMN {col} DOUBLE")
                            elif col == 'leverage':
                                conn.execute(f"ALTER TABLE trade_history ADD COLUMN {col} INT")
                            elif col == 'reason':
                                conn.execute(f"ALTER TABLE trade_history ADD COLUMN {col} VARCHAR(255)")
                        conn.commit()
                    logger.info(f"Added new columns to trade_history table: {', '.join(need_add)}")
                except Exception as e:
                    logger.debug(f"Error adding columns (may already exist): {e}")
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def close(self):
        """Close database connections"""
        self.engine.dispose()

