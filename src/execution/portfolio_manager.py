"""Portfolio and position management."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Manage portfolio state and performance tracking."""
    
    def __init__(self, initial_balance: float = None, db = None):
        self.initial_balance = initial_balance  # Will be set from first account fetch if None
        self.trade_history: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.start_time = datetime.now()
        self._initial_balance_set = (initial_balance is not None)
        self._last_total_value = initial_balance or 0  # Cache last calculated total value
        self._db = db  # Database reference for persisting initial_balance
    
    def calculate_account_state(
        self,
        balance: Dict,
        positions: List[Dict],
        realtime_prices: Dict[str, float] = None
    ) -> Dict:
        """
        Calculate current account state with real-time prices.
        
        Args:
            balance: Balance dict from exchange
            positions: List of current positions
            realtime_prices: Dict of real-time prices from WebSocket {symbol: price}
        
        Returns:
            Dict with account metrics
        """
        # Get USDT balance
        usdt_balance = balance.get('USDT', {})
        
        # ✅ Use total balance (free + used margin), not just free
        # This ensures account value doesn't drop when opening positions
        wallet_balance = usdt_balance.get('total', 0)
        if wallet_balance == 0:
            # Fallback: calculate from free + used
            wallet_balance = usdt_balance.get('free', 0) + usdt_balance.get('used', 0)
        
        available_cash = usdt_balance.get('free', 0)  # Still track for reference
        
        # Calculate total unrealized PnL using real-time prices if available
        total_unrealized_pnl = 0.0
        
        for pos in positions:
            contracts = float(pos.get('contracts', 0))
            if contracts == 0:
                continue
                
            entry_price = float(pos.get('entryPrice', 0))
            symbol = pos.get('symbol', '')
            side = pos.get('side', 'long')
            
            # Use real-time price if available, otherwise fall back to exchange's markPrice
            if realtime_prices and symbol in realtime_prices:
                current_price = realtime_prices[symbol]
                # Calculate unrealized PnL based on position side
                if side == 'long':
                    pnl = contracts * (current_price - entry_price)
                else:  # short
                    pnl = contracts * (entry_price - current_price)
                total_unrealized_pnl += pnl
            else:
                # Fallback to exchange's unrealizedPnl
                total_unrealized_pnl += float(pos.get('unrealizedPnl', 0))
        
        # Calculate total account value
        # ✅ Use wallet_balance (包含已用保证金) instead of available_cash
        # This way account value stays constant when opening/closing positions
        total_value = wallet_balance + total_unrealized_pnl
        
        # Set initial balance from first account fetch (for Live/Testnet mode)
        # IMPORTANT: Use total_value (not just free balance) to handle existing positions correctly
        if not self._initial_balance_set:
            # Try to load from database first
            if self._db:
                saved_initial = self._db.get_config('initial_balance')
                if saved_initial:
                    self.initial_balance = float(saved_initial)
                    logger.info(f"📊 Loaded initial balance from DB: ${self.initial_balance:.2f} USDT")
                else:
                    # First time setup: save to database
                    self.initial_balance = total_value
                    self._db.set_config('initial_balance', str(total_value))
                    logger.info(f"📊 Initial balance set and saved to DB: ${self.initial_balance:.2f} USDT")
            else:
                # No database, use current total value
                self.initial_balance = total_value
                logger.info(f"📊 Initial balance set from account: ${self.initial_balance:.2f} USDT")
            
            self._initial_balance_set = True
        
        # Calculate return
        total_return = ((total_value - self.initial_balance) / self.initial_balance) * 100
        
        # Calculate Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio()
        
        # Record equity curve
        self.equity_curve.append({
            'timestamp': datetime.now(),
            'value': total_value,
            'cash': available_cash,
            'unrealized_pnl': total_unrealized_pnl
        })
        
        # Cache the total value for later use
        self._last_total_value = total_value
        
        return {
            'cash': available_cash,           # 可用余额（可开仓的）
            'wallet_balance': wallet_balance,  # 钱包余额（free + used）
            'total_value': total_value,        # 总资产（wallet + unrealized_pnl）
            'total_return': total_return,
            'unrealized_pnl': total_unrealized_pnl,
            'sharpe_ratio': sharpe_ratio,
            'num_positions': len(positions)
        }
    
    def get_total_value(self) -> float:
        """
        Get the last calculated total account value.
        
        Returns:
            float: Total account value in USDT
        """
        return self._last_total_value
    
    def format_positions_for_prompt(self, positions: List[Dict]) -> List[Dict]:
        """
        Format positions for AI prompt (matching nof1.ai format).
        
        Args:
            positions: Raw positions from exchange
        
        Returns:
            List of formatted position dicts
        """
        formatted = []
        
        # Safe conversion helpers (handle None values from API)
        def safe_float(value, default=0.0):
            """Convert to float, handling None values."""
            if value is None:
                return default
            try:
                return float(value)
            except (ValueError, TypeError):
                return default
        
        def safe_int(value, default=1):
            """Convert to int, handling None values."""
            if value is None:
                return default
            try:
                return int(value)
            except (ValueError, TypeError):
                return default
        
        for pos in positions:
            # Extract relevant fields
            symbol = pos.get('symbol', '').replace('/USDT:USDT', '')
            contracts = safe_float(pos.get('contracts', 0))
            
            if contracts == 0:
                continue
            
            # Get position side (long or short)
            side = pos.get('side', 'long')
            
            # IMPORTANT: Store quantity with sign
            # Positive quantity = long position
            # Negative quantity = short position
            if side == 'short':
                quantity = -abs(contracts)
            else:
                quantity = abs(contracts)
            
            # Use safe conversion helpers
            entry_price = safe_float(pos.get('entryPrice', 0))
            current_price = safe_float(pos.get('markPrice', 0))
            liquidation_price = safe_float(pos.get('liquidationPrice', 0))
            unrealized_pnl = safe_float(pos.get('unrealizedPnl', 0))
            leverage = safe_int(pos.get('leverage', 1))
            notional = safe_float(pos.get('notional', 0))
            
            # Calculate from stored exit plan if available
            # In production, you'd store this in a database
            # For now, we'll use placeholder values
            # Get entry timestamp (for trade duration calculation)
            timestamp = pos.get('timestamp') or pos.get('updateTime')
            
            # Calculate holding time and PnL percentage
            holding_time_str = "Unknown"
            pnl_percent = 0.0
            
            try:
                if timestamp:
                    from datetime import datetime
                    # Handle different timestamp formats
                    if isinstance(timestamp, (int, float)):
                        entry_time = datetime.fromtimestamp(timestamp / 1000 if timestamp > 1e10 else timestamp)
                    elif isinstance(timestamp, str):
                        try:
                            # Try parsing ISO format
                            entry_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        except:
                            # Try parsing as timestamp
                            ts = float(timestamp)
                            entry_time = datetime.fromtimestamp(ts / 1000 if ts > 1e10 else ts)
                    else:
                        entry_time = timestamp
                    
                    # Calculate holding duration
                    holding_duration = datetime.now() - entry_time
                    total_minutes = int(holding_duration.total_seconds() / 60)
                    
                    if total_minutes >= 60:
                        hours = total_minutes // 60
                        minutes = total_minutes % 60
                        holding_time_str = f"{hours}h {minutes}m"
                    else:
                        holding_time_str = f"{total_minutes}m"
                        
                # Calculate PnL percentage
                if entry_price > 0 and abs(quantity) > 0:
                    investment = entry_price * abs(quantity)
                    pnl_percent = (unrealized_pnl / investment) * 100 if investment > 0 else 0.0
                    
            except Exception as e:
                # Fallback to safe defaults
                holding_time_str = "Unknown"
                pnl_percent = 0.0
            
            formatted_pos = {
                'symbol': symbol,
                'quantity': quantity,  # With sign: + for long, - for short
                'side': side,  # Keep side info for reference
                'entry_price': entry_price,
                'current_price': current_price,
                'unrealized_pnl': unrealized_pnl,
                'pnl_percent': round(pnl_percent, 2),  # 🆕 收益率百分比
                'holding_time': holding_time_str,      # 🆕 持仓时长
                'leverage': leverage,
                'notional_usd': abs(notional),
                'liquidation_price': liquidation_price,
                'timestamp': timestamp,  # Keep original for debugging
                'exit_plan': {
                    'profit_target': 0,  # To be filled from database
                    'stop_loss': 0,
                    'invalidation_condition': ''
                },
                'confidence': 0.75,  # Default
                'risk_usd': 0,
                'sl_oid': -1,
                'tp_oid': -1,
                'wait_for_fill': False,
                'entry_oid': -1
            }
            
            formatted.append(formatted_pos)
        
        return formatted
    
    def record_trade(
        self,
        coin: str,
        action: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None
    ):
        """Record a trade in history."""
        trade = {
            'timestamp': datetime.now(),
            'coin': coin,
            'action': action,
            'quantity': quantity,
            'price': price,
            'pnl': pnl
        }
        
        self.trade_history.append(trade)
        logger.info(f"Trade recorded: {action} {quantity} {coin} @ {price}")
    
    def _calculate_sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio from equity curve."""
        if len(self.equity_curve) < 2:
            return 0.0
        
        # Get returns
        values = [e['value'] for e in self.equity_curve]
        returns = np.diff(values) / values[:-1]
        
        if len(returns) == 0:
            return 0.0
        
        # Calculate excess returns
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate
        
        # Sharpe ratio = mean(excess returns) / std(excess returns)
        if np.std(excess_returns) == 0:
            return 0.0
        
        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        
        # Annualize (assuming we sample at decision interval, ~2.6 min)
        # There are ~221 trading intervals per day (24*60/2.6)
        annualization_factor = np.sqrt(221 * 365)
        
        return sharpe * annualization_factor
    
    def get_performance_metrics(self) -> Dict:
        """Get comprehensive performance metrics."""
        if len(self.equity_curve) == 0:
            return {}
        
        values = [e['value'] for e in self.equity_curve]
        
        # Calculate drawdown
        peak = values[0]
        max_drawdown = 0
        current_drawdown = 0
        
        for value in values:
            if value > peak:
                peak = value
            
            drawdown = (peak - value) / peak * 100
            current_drawdown = drawdown
            
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Win rate
        closed_trades = [t for t in self.trade_history if t.get('pnl') is not None]
        winning_trades = [t for t in closed_trades if t['pnl'] > 0]
        win_rate = len(winning_trades) / len(closed_trades) if closed_trades else 0
        
        # Total PnL
        total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
        
        return {
            'total_trades': len(closed_trades),
            'win_rate': win_rate * 100,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'current_value': values[-1],
            'peak_value': peak
        }

