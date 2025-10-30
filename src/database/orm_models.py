"""
SQLAlchemy ORM Models for Trading Bot
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class AccountState(Base):
    """账户状态表"""
    __tablename__ = 'account_state'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    num_positions = Column(Integer, nullable=False)
    available_balance = Column(Float, nullable=False)
    used_balance = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'total_value': self.total_value,
            'total_return': self.total_return,
            'num_positions': self.num_positions,
            'available_balance': self.available_balance,
            'used_balance': self.used_balance,
            'unrealized_pnl': self.unrealized_pnl
        }


class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = 'system_config'
    
    key = Column(String(255), primary_key=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class CoinPrice(Base):
    """币种价格表"""
    __tablename__ = 'coin_prices'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    price = Column(Float, nullable=False)
    rsi_14 = Column(Float)
    macd = Column(Float)
    funding_rate = Column(Float)
    open_interest = Column(Float)
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': self.symbol,
            'price': self.price,
            'rsi_14': self.rsi_14,
            'macd': self.macd,
            'funding_rate': self.funding_rate,
            'open_interest': self.open_interest
        }


class AIDecision(Base):
    """AI决策表"""
    __tablename__ = 'ai_decisions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    coin = Column(String(50), nullable=False, index=True)
    decision = Column(String(50))
    side = Column(String(10))
    confidence = Column(Float)
    leverage = Column(Integer)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    risk_usd = Column(Float)
    reasoning = Column(Text)
    thinking = Column(Text)
    executed = Column(Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'coin': self.coin,
            'decision': self.decision,
            'side': self.side,
            'confidence': self.confidence,
            'leverage': self.leverage,
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'risk_usd': self.risk_usd,
            'reasoning': self.reasoning,
            'thinking': self.thinking,
            'executed': self.executed
        }


class Position(Base):
    """持仓表"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10))
    quantity = Column(Float)
    entry_price = Column(Float)
    current_price = Column(Float)
    leverage = Column(Integer)
    unrealized_pnl = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    active = Column(Boolean, default=True, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'current_price': self.current_price,
            'leverage': self.leverage,
            'unrealized_pnl': self.unrealized_pnl,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'active': self.active
        }


class TradeHistory(Base):
    """交易历史表"""
    __tablename__ = 'trade_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    close_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    entry_timestamp = Column(DateTime)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(10))
    quantity = Column(Float)
    entry_price = Column(Float)
    exit_price = Column(Float)
    entry_notional = Column(Float)
    exit_notional = Column(Float)
    leverage = Column(Integer)
    pnl = Column(Float)
    pnl_percent = Column(Float)
    duration_minutes = Column(Integer)
    reason = Column(String(255))
    
    def to_dict(self):
        return {
            'id': self.id,
            'close_timestamp': self.close_timestamp.isoformat() if self.close_timestamp else None,
            'entry_timestamp': self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'entry_notional': self.entry_notional,
            'exit_notional': self.exit_notional,
            'leverage': self.leverage,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'duration_minutes': self.duration_minutes,
            'reason': self.reason
        }

