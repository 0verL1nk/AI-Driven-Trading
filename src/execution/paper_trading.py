"""Paper trading simulator for backtesting and testing."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """Represents a paper trading position."""
    symbol: str
    quantity: float
    entry_price: float
    leverage: int
    side: str  # 'long' or 'short'
    entry_time: datetime
    stop_loss: float
    take_profit: float
    invalidation_condition: str
    confidence: float
    risk_usd: float
    entry_oid: int
    sl_oid: int = -1
    tp_oid: int = -1


@dataclass
class PaperOrder:
    """Represents a paper trading order."""
    order_id: int
    symbol: str
    side: str  # 'buy' or 'sell'
    amount: float
    order_type: str  # 'market', 'stop', 'take_profit'
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: str = 'open'  # 'open', 'filled', 'cancelled'
    filled_time: Optional[datetime] = None


class PaperTradingEngine:
    """
    Simulated exchange for paper trading.
    Mimics real exchange behavior without real money.
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        maker_fee: float = 0.0002,  # 0.02%
        taker_fee: float = 0.0004,  # 0.04%
        slippage: float = 0.001     # 0.1%
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage = slippage
        
        self.positions: Dict[str, PaperPosition] = {}
        self.orders: Dict[int, PaperOrder] = {}
        self.order_counter = 1
        self.trade_history: List[Dict] = []
    
    async def fetch_balance(self) -> Dict:
        """Get simulated balance."""
        # Calculate unrealized PnL from positions
        unrealized_pnl = sum(
            self._calculate_position_pnl(pos, self._get_current_price(pos.symbol))
            for pos in self.positions.values()
        )
        
        # Used margin
        used_margin = sum(
            abs(pos.quantity * pos.entry_price) / pos.leverage
            for pos in self.positions.values()
        )
        
        total = self.balance + unrealized_pnl
        free = self.balance - used_margin
        
        return {
            'total': {'USDT': total},
            'free': {'USDT': free},
            'used': {'USDT': used_margin},
            'USDT': {
                'free': free,
                'used': used_margin,
                'total': total
            }
        }
    
    async def fetch_positions(self) -> List[Dict]:
        """Get simulated positions."""
        positions_list = []
        
        for symbol, pos in self.positions.items():
            current_price = self._get_current_price(symbol)
            unrealized_pnl = self._calculate_position_pnl(pos, current_price)
            
            notional = pos.quantity * current_price
            
            positions_list.append({
                'symbol': symbol,
                'contracts': pos.quantity,
                'contractSize': 1,
                'unrealizedPnl': unrealized_pnl,
                'leverage': pos.leverage,
                'liquidationPrice': self._calculate_liquidation_price(pos),
                'entryPrice': pos.entry_price,
                'markPrice': current_price,
                'notional': notional,
                'side': pos.side,
                'timestamp': pos.entry_time.timestamp() * 1000
            })
        
        return positions_list
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """Simulate market order execution."""
        order_id = self.order_counter
        self.order_counter += 1
        
        # Get current price with slippage
        base_price = self._get_current_price(symbol)
        if side == 'buy':
            fill_price = base_price * (1 + self.slippage)
        else:
            fill_price = base_price * (1 - self.slippage)
        
        # Calculate fee (taker fee for market orders)
        notional = amount * fill_price
        fee = notional * self.taker_fee
        
        # Update balance
        if side == 'buy':
            # Opening long or closing short
            if symbol in self.positions and self.positions[symbol].side == 'short':
                # Closing short
                pos = self.positions[symbol]
                pnl = self._calculate_position_pnl(pos, fill_price)
                self.balance += pnl - fee
                del self.positions[symbol]
                
                logger.info(f"Closed SHORT {symbol}: PnL = ${pnl:.2f}")
            else:
                # Opening long
                self.balance -= fee
        else:
            # Opening short or closing long
            if symbol in self.positions and self.positions[symbol].side == 'long':
                # Closing long
                pos = self.positions[symbol]
                pnl = self._calculate_position_pnl(pos, fill_price)
                self.balance += pnl - fee
                del self.positions[symbol]
                
                logger.info(f"Closed LONG {symbol}: PnL = ${pnl:.2f}")
            else:
                # Opening short
                self.balance -= fee
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            amount=amount,
            order_type='market',
            price=fill_price,
            status='filled',
            filled_time=datetime.now()
        )
        
        self.orders[order_id] = order
        
        return {
            'id': str(order_id),
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': fill_price,
            'type': 'market',
            'status': 'closed',
            'filled': amount,
            'cost': notional,
            'fee': {'cost': fee, 'currency': 'USDT'}
        }
    
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Dict:
        """Simulate stop loss order."""
        order_id = self.order_counter
        self.order_counter += 1
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            amount=amount,
            order_type='stop',
            trigger_price=stop_price,
            status='open'
        )
        
        self.orders[order_id] = order
        
        return {
            'id': str(order_id),
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'stopPrice': stop_price,
            'type': 'stop',
            'status': 'open'
        }
    
    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float
    ) -> Dict:
        """Simulate take profit order."""
        order_id = self.order_counter
        self.order_counter += 1
        
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            side=side,
            amount=amount,
            order_type='take_profit',
            trigger_price=take_profit_price,
            status='open'
        )
        
        self.orders[order_id] = order
        
        return {
            'id': str(order_id),
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'stopPrice': take_profit_price,
            'type': 'take_profit',
            'status': 'open'
        }
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage (simulated, just returns success)."""
        return {'leverage': leverage, 'symbol': symbol}
    
    def update_position(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        leverage: int,
        side: str,
        stop_loss: float,
        take_profit: float,
        invalidation_condition: str,
        confidence: float,
        risk_usd: float,
        entry_oid: int,
        sl_oid: int = -1,
        tp_oid: int = -1
    ):
        """Manually update position (for tracking purposes)."""
        self.positions[symbol] = PaperPosition(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            leverage=leverage,
            side=side,
            entry_time=datetime.now(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            invalidation_condition=invalidation_condition,
            confidence=confidence,
            risk_usd=risk_usd,
            entry_oid=entry_oid,
            sl_oid=sl_oid,
            tp_oid=tp_oid
        )
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price (would be from market data in real usage)."""
        # This is a placeholder - in real usage, you'd fetch from market data
        # For now, return a default price
        return 100.0
    
    def _calculate_position_pnl(self, pos: PaperPosition, current_price: float) -> float:
        """Calculate position PnL."""
        if pos.side == 'long':
            pnl = (current_price - pos.entry_price) * pos.quantity
        else:  # short
            pnl = (pos.entry_price - current_price) * pos.quantity
        
        return pnl
    
    def _calculate_liquidation_price(self, pos: PaperPosition) -> float:
        """Calculate liquidation price."""
        # Simplified liquidation price calculation
        # Liquidation occurs when losses = initial margin
        initial_margin_percent = 1 / pos.leverage
        
        if pos.side == 'long':
            # For long: liq_price = entry * (1 - initial_margin%)
            liq_price = pos.entry_price * (1 - initial_margin_percent * 0.9)
        else:
            # For short: liq_price = entry * (1 + initial_margin%)
            liq_price = pos.entry_price * (1 + initial_margin_percent * 0.9)
        
        return liq_price
    
    async def close(self):
        """Close connection (no-op for paper trading)."""
        pass

