"""
Trading Database Manager using SQLAlchemy ORM
支持 SQLite 和 MySQL
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from .session import DatabaseManager
from .orm_models import (
    AccountState, SystemConfig, CoinPrice, AIDecision, 
    Position, TradeHistory
)

logger = logging.getLogger(__name__)


class TradingDatabase:
    """Trading bot数据库管理器 - 使用ORM"""
    
    def __init__(self, db_type: str = "sqlite", **kwargs):
        """
        Initialize database.
        
        Args:
            db_type: 'sqlite' or 'mysql'
            **kwargs: Database-specific parameters
                - For SQLite: db_path (default: "trading_data.db")
                - For MySQL: host, port, user, password, database
        """
        self.db_manager = DatabaseManager(db_type, **kwargs)
        self.db_type = db_type.lower()
    
    def init_database(self):
        """初始化数据库表（已由DatabaseManager处理）"""
        pass
    
    def save_account_state(self, state: Dict):
        """保存账户状态"""
        session = self.db_manager.get_session()
        try:
            account_state = AccountState(
                total_value=state.get('total_value', 0),
                total_return=state.get('total_return', 0),
                num_positions=state.get('num_positions', 0),
                available_balance=state.get('available_balance', 0),
                used_balance=state.get('used_balance', 0),
                unrealized_pnl=state.get('unrealized_pnl', 0)
            )
            session.add(account_state)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving account state: {e}")
            raise
        finally:
            session.close()
    
    def save_coin_price(self, symbol: str, price_data: Dict):
        """保存币种价格数据"""
        session = self.db_manager.get_session()
        try:
            coin_price = CoinPrice(
                symbol=symbol,
                price=price_data.get('price', 0),
                rsi_14=price_data.get('rsi_14', 0),
                macd=price_data.get('macd', 0),
                funding_rate=price_data.get('funding_rate', 0),
                open_interest=price_data.get('open_interest', 0)
            )
            session.add(coin_price)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving coin price: {e}")
            raise
        finally:
            session.close()
    
    def save_ai_decision(self, coin: str, decision: Dict, thinking: str = ""):
        """保存AI决策"""
        if not isinstance(decision, dict):
            logger.warning(f"save_ai_decision: decision for {coin} is not a dict, got {type(decision)}")
            return
        
        args = decision.get('trade_signal_args', {})
        
        session = self.db_manager.get_session()
        try:
            ai_decision = AIDecision(
                coin=coin,
                decision=args.get('signal', 'hold') if args else decision.get('decision', 'hold'),
                side=decision.get('side', ''),
                confidence=args.get('confidence', 0) if args else decision.get('confidence', 0),
                leverage=args.get('leverage', 0) if args else decision.get('leverage', 0),
                entry_price=args.get('entry_price', 0) if args else decision.get('entry_price', 0),
                stop_loss=args.get('stop_loss', 0) if args else decision.get('stop_loss', 0),
                take_profit=(args.get('take_profit') or args.get('profit_target', 0)) if args 
                           else (decision.get('take_profit') or decision.get('profit_target', 0)),
                risk_usd=args.get('risk_usd', 0) if args else decision.get('risk_usd', 0),
                reasoning=decision.get('reasoning', ''),
                thinking=thinking,
                executed=decision.get('executed', False)
            )
            session.add(ai_decision)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving AI decision: {e}")
            raise
        finally:
            session.close()
    
    def save_position(self, position: Dict):
        """保存持仓信息"""
        session = self.db_manager.get_session()
        try:
            db_position = Position(
                symbol=position.get('symbol', ''),
                side=position.get('side', ''),
                quantity=position.get('quantity', 0),
                entry_price=position.get('entry_price', 0),
                current_price=position.get('current_price', 0),
                leverage=position.get('leverage', 0),
                unrealized_pnl=position.get('unrealized_pnl', 0),
                stop_loss=position.get('stop_loss', 0),
                take_profit=position.get('take_profit', 0),
                active=position.get('active', True)
            )
            session.add(db_position)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving position: {e}")
            raise
        finally:
            session.close()
    
    def get_latest_account_state(self) -> Optional[Dict]:
        """获取最新账户状态"""
        session = self.db_manager.get_session()
        try:
            account_state = session.query(AccountState).order_by(
                AccountState.timestamp.desc()
            ).first()
            return account_state.to_dict() if account_state else None
        finally:
            session.close()
    
    def get_latest_prices(self) -> List[Dict]:
        """获取最新价格（每个币种最新一条）"""
        session = self.db_manager.get_session()
        try:
            # 使用子查询获取每个symbol的最新记录
            subquery = session.query(
                CoinPrice.symbol,
                func.max(CoinPrice.timestamp).label('max_timestamp')
            ).group_by(CoinPrice.symbol).subquery()
            
            latest_prices = session.query(CoinPrice).join(
                subquery,
                and_(
                    CoinPrice.symbol == subquery.c.symbol,
                    CoinPrice.timestamp == subquery.c.max_timestamp
                )
            ).order_by(CoinPrice.symbol).all()
            
            return [price.to_dict() for price in latest_prices]
        finally:
            session.close()
    
    def get_recent_decisions(self, limit: int = 20) -> List[Dict]:
        """获取最近的AI决策"""
        session = self.db_manager.get_session()
        try:
            decisions = session.query(AIDecision).order_by(
                AIDecision.timestamp.desc()
            ).limit(limit).all()
            return [d.to_dict() for d in decisions]
        finally:
            session.close()
    
    def get_active_positions(self) -> List[Dict]:
        """获取活跃持仓"""
        session = self.db_manager.get_session()
        try:
            positions = session.query(Position).filter(
                Position.active == True
            ).order_by(Position.timestamp.desc()).all()
            return [p.to_dict() for p in positions]
        finally:
            session.close()
    
    def get_account_history(self, hours: int = 24, mode: str = 'auto') -> List[Dict]:
        """
        获取账户历史（用于图表）- 智能采样保持曲线完整性
        """
        session = self.db_manager.get_session()
        try:
            # 计算时间范围
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            if mode == 'full':
                # 返回全部数据
                account_states = session.query(AccountState).filter(
                    AccountState.timestamp >= time_threshold
                ).order_by(AccountState.timestamp.asc()).all()
                return [state.to_dict() for state in account_states]
            
            elif mode == 'fast':
                # 快速模式：最多200个点
                total_count = session.query(AccountState).filter(
                    AccountState.timestamp >= time_threshold
                ).count()
                
                if total_count <= 200:
                    account_states = session.query(AccountState).filter(
                        AccountState.timestamp >= time_threshold
                    ).order_by(AccountState.timestamp.asc()).all()
                else:
                    # 采样：每N个取1个
                    step = max(1, total_count // 200)
                    account_states = session.query(AccountState).filter(
                        AccountState.timestamp >= time_threshold
                    ).order_by(AccountState.timestamp.asc()).all()[::step]
                    # 确保不超过200个
                    account_states = account_states[:200]
                
                return [state.to_dict() for state in account_states]
            
            else:  # mode == 'auto'
                # 智能采样：根据时间范围动态调整密度
                target_points = 1000
                if hours <= 1:
                    target_points = 2000
                elif hours <= 6:
                    target_points = 1500
                elif hours <= 24:
                    target_points = 1000
                else:
                    target_points = 800
                
                total_count = session.query(AccountState).filter(
                    AccountState.timestamp >= time_threshold
                ).count()
                
                if total_count <= target_points:
                    account_states = session.query(AccountState).filter(
                        AccountState.timestamp >= time_threshold
                    ).order_by(AccountState.timestamp.asc()).all()
                else:
                    # 采样：每N个取1个，但保留第一个和最后一个
                    step = max(1, total_count // target_points)
                    all_states = session.query(AccountState).filter(
                        AccountState.timestamp >= time_threshold
                    ).order_by(AccountState.timestamp.asc()).all()
                    
                    # 采样并保留转折点
                    sampled = []
                    for i, state in enumerate(all_states):
                        if i == 0 or i == len(all_states) - 1:
                            # 保留第一个和最后一个
                            sampled.append(state)
                        elif i % step == 0:
                            # 采样点
                            sampled.append(state)
                        elif i > 0 and i < len(all_states) - 1:
                            # 检查是否是转折点
                            prev_value = all_states[i-1].total_value
                            next_value = all_states[i+1].total_value
                            curr_value = state.total_value
                            
                            # 如果价值变化方向改变，保留这个点
                            if abs(curr_value - prev_value) > abs(next_value - curr_value) * 1.5:
                                sampled.append(state)
                    
                    account_states = sampled[:target_points + 100]
                
                return [state.to_dict() for state in account_states]
        finally:
            session.close()
    
    def get_account_history_since(self, since_timestamp: str) -> List[Dict]:
        """获取指定时间戳之后的账户历史（增量查询）"""
        session = self.db_manager.get_session()
        try:
            if isinstance(since_timestamp, str):
                since_dt = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
            else:
                since_dt = since_timestamp
            
            account_states = session.query(AccountState).filter(
                AccountState.timestamp > since_dt
            ).order_by(AccountState.timestamp.asc()).all()
            return [state.to_dict() for state in account_states]
        finally:
            session.close()
    
    def get_price_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """获取价格历史"""
        session = self.db_manager.get_session()
        try:
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            prices = session.query(CoinPrice).filter(
                and_(
                    CoinPrice.symbol == symbol,
                    CoinPrice.timestamp >= time_threshold
                )
            ).order_by(CoinPrice.timestamp.asc()).all()
            return [p.to_dict() for p in prices]
        finally:
            session.close()
    
    def get_config(self, key: str) -> Optional[str]:
        """获取系统配置"""
        session = self.db_manager.get_session()
        try:
            config = session.query(SystemConfig).filter(
                SystemConfig.key == key
            ).first()
            return config.value if config else None
        finally:
            session.close()
    
    def set_config(self, key: str, value: str):
        """设置系统配置"""
        session = self.db_manager.get_session()
        try:
            config = session.query(SystemConfig).filter(
                SystemConfig.key == key
            ).first()
            
            if config:
                config.value = value
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(key=key, value=value)
                session.add(config)
            
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error setting config: {e}")
            raise
        finally:
            session.close()
    
    def delete_config(self, key: str):
        """删除系统配置"""
        session = self.db_manager.get_session()
        try:
            session.query(SystemConfig).filter(
                SystemConfig.key == key
            ).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting config: {e}")
            raise
        finally:
            session.close()
    
    def save_trade(self, trade: Dict):
        """保存交易历史"""
        session = self.db_manager.get_session()
        try:
            trade_history = TradeHistory(
                entry_timestamp=trade.get('entry_timestamp'),
                symbol=trade.get('symbol'),
                side=trade.get('side'),
                quantity=trade.get('quantity'),
                entry_price=trade.get('entry_price'),
                exit_price=trade.get('exit_price'),
                entry_notional=trade.get('entry_notional'),
                exit_notional=trade.get('exit_notional'),
                leverage=trade.get('leverage'),
                pnl=trade.get('pnl'),
                pnl_percent=trade.get('pnl_percent'),
                duration_minutes=trade.get('duration_minutes'),
                reason=trade.get('reason', 'manual_close')
            )
            session.add(trade_history)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trade: {e}")
            raise
        finally:
            session.close()
    
    def get_trade_history(self, limit: int = 50) -> List[Dict]:
        """获取交易历史（兼容旧接口）"""
        session = self.db_manager.get_session()
        try:
            trades = session.query(TradeHistory).order_by(
                TradeHistory.close_timestamp.desc()
            ).limit(limit).all()
            return [t.to_dict() for t in trades]
        finally:
            session.close()
    
    def get_trade_history_paginated(self, offset: int, limit: int) -> List[Dict]:
        """获取交易历史（分页）"""
        session = self.db_manager.get_session()
        try:
            trades = session.query(TradeHistory).order_by(
                TradeHistory.close_timestamp.desc()
            ).offset(offset).limit(limit).all()
            return [t.to_dict() for t in trades]
        finally:
            session.close()
    
    def get_trades_count(self) -> int:
        """获取交易总数"""
        session = self.db_manager.get_session()
        try:
            return session.query(TradeHistory).count()
        finally:
            session.close()
    
    def _save_positions_to_db(self, positions, realtime_prices):
        """保存持仓数据到数据库（供前端显示）"""
        session = self.db_manager.get_session()
        try:
            # 先清空旧的活跃持仓记录
            session.query(Position).filter(Position.active == True).delete()
            
            # 保存当前持仓
            for pos in positions:
                contracts = pos.get('contracts', 0)
                if not contracts or contracts == 0:
                    continue
                
                symbol = pos.get('symbol', '')
                entry_price = pos.get('entryPrice', 0)
                current_price = realtime_prices.get(symbol, pos.get('markPrice', 0))
                
                side = pos.get('side', 'long')
                if side == 'long':
                    unrealized_pnl = contracts * (current_price - entry_price)
                else:
                    unrealized_pnl = contracts * (entry_price - current_price)
                
                db_position = Position(
                    symbol=symbol,
                    side=side,
                    quantity=contracts,
                    entry_price=entry_price,
                    current_price=current_price,
                    leverage=pos.get('leverage', 1),
                    unrealized_pnl=unrealized_pnl,
                    stop_loss=0,
                    take_profit=0,
                    active=True
                )
                session.add(db_position)
            
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving positions to DB: {e}")
            raise
        finally:
            session.close()
