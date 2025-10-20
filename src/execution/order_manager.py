"""Order execution and management."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..data.exchange_client import ExchangeClient
from ..config import trading_config

logger = logging.getLogger(__name__)


class OrderManager:
    """Manage order execution and tracking."""
    
    def __init__(self, exchange_client: ExchangeClient):
        self.exchange = exchange_client
        self.active_orders: Dict[str, List[Dict]] = {}  # coin -> list of orders
    
    async def execute_entry(
        self,
        coin: str,
        symbol: str,
        side: str,
        quantity: float,
        leverage: int,
        stop_loss: float,
        take_profit: float
    ) -> Dict:
        """
        Execute entry order with stop loss and take profit.
        
        Args:
            coin: Coin symbol (e.g., 'BTC')
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            side: 'buy' or 'sell'
            quantity: Position size in base currency
            leverage: Leverage multiplier
            stop_loss: Stop loss price
            take_profit: Take profit price
        
        Returns:
            Dict with entry order, SL order, and TP order info
        """
        try:
            # Set leverage
            await self.exchange.set_leverage(symbol, leverage)
            logger.info(f"Set leverage to {leverage}x for {symbol}")
            
            # Execute market entry order
            entry_order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=quantity
            )
            
            logger.info(f"Entry order executed: {entry_order['id']} - {side} {quantity} {symbol}")
            
            # Wait a moment for order to fill
            await asyncio.sleep(1)
            
            # Determine SL/TP sides
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            # Create stop loss order
            sl_order = await self.exchange.create_stop_loss_order(
                symbol=symbol,
                side=sl_side,
                amount=quantity,
                stop_price=stop_loss
            )
            
            logger.info(f"Stop loss set at {stop_loss} (order {sl_order['id']})")
            
            # Create take profit order
            tp_order = await self.exchange.create_take_profit_order(
                symbol=symbol,
                side=sl_side,
                amount=quantity,
                take_profit_price=take_profit
            )
            
            logger.info(f"Take profit set at {take_profit} (order {tp_order['id']})")
            
            # Track orders
            if coin not in self.active_orders:
                self.active_orders[coin] = []
            
            self.active_orders[coin].extend([
                {'type': 'entry', 'order': entry_order},
                {'type': 'stop_loss', 'order': sl_order},
                {'type': 'take_profit', 'order': tp_order}
            ])
            
            return {
                'entry_order': entry_order,
                'sl_order': sl_order,
                'tp_order': tp_order,
                'entry_oid': entry_order['id'],
                'sl_oid': sl_order['id'],
                'tp_oid': tp_order['id']
            }
        
        except Exception as e:
            logger.error(f"Failed to execute entry for {coin}: {e}")
            raise
    
    async def execute_close(
        self,
        coin: str,
        symbol: str,
        position: Dict
    ) -> Dict:
        """
        Close existing position.
        
        Args:
            coin: Coin symbol
            symbol: Trading pair
            position: Position info dict
        
        Returns:
            Close order info
        """
        try:
            quantity = position.get('quantity', 0)
            
            if quantity == 0:
                logger.warning(f"No position to close for {coin}")
                return {}
            
            # Determine close side (opposite of position)
            # If we're long (quantity > 0), we sell to close
            # If we're short (quantity < 0), we buy to close
            side = 'sell' if quantity > 0 else 'buy'
            amount = abs(quantity)
            
            # Cancel existing SL/TP orders
            await self._cancel_pending_orders(coin, symbol)
            
            # Execute market close order
            close_order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount
            )
            
            logger.info(f"Position closed: {close_order['id']} - {side} {amount} {symbol}")
            
            # Remove from active orders
            if coin in self.active_orders:
                del self.active_orders[coin]
            
            return {'close_order': close_order}
        
        except Exception as e:
            logger.error(f"Failed to close position for {coin}: {e}")
            raise
    
    async def _cancel_pending_orders(self, coin: str, symbol: str):
        """Cancel pending SL/TP orders for a coin."""
        if coin not in self.active_orders:
            return
        
        for order_info in self.active_orders[coin]:
            if order_info['type'] in ['stop_loss', 'take_profit']:
                try:
                    order_id = order_info['order']['id']
                    await self.exchange.exchange.cancel_order(order_id, symbol)
                    logger.info(f"Cancelled {order_info['type']} order {order_id}")
                except Exception as e:
                    logger.warning(f"Failed to cancel order {order_id}: {e}")
    
    async def check_invalidation_conditions(
        self,
        positions: List[Dict],
        current_prices: Dict[str, float]
    ) -> List[str]:
        """
        Check if any position's invalidation condition is triggered.
        
        Args:
            positions: List of position dicts with 'invalidation_condition'
            current_prices: Dict of coin -> current price
        
        Returns:
            List of coins that should be closed due to invalidation
        """
        to_close = []
        
        for position in positions:
            coin = position.get('symbol', '').replace('/USDT:USDT', '')
            
            if coin not in current_prices:
                continue
            
            current_price = current_prices[coin]
            invalidation = position.get('exit_plan', {}).get('invalidation_condition', '')
            
            # Parse invalidation condition
            # Example: "If the price closes below 3800 on a 3-minute candle"
            if 'closes below' in invalidation.lower():
                try:
                    # Extract threshold price
                    parts = invalidation.split('below')
                    if len(parts) > 1:
                        threshold_str = parts[1].split('on')[0].strip()
                        threshold = float(threshold_str)
                        
                        if current_price < threshold:
                            logger.warning(
                                f"{coin} invalidation triggered: price {current_price} "
                                f"below threshold {threshold}"
                            )
                            to_close.append(coin)
                
                except (ValueError, IndexError) as e:
                    logger.error(f"Failed to parse invalidation condition: {invalidation} - {e}")
            
            elif 'closes above' in invalidation.lower():
                try:
                    parts = invalidation.split('above')
                    if len(parts) > 1:
                        threshold_str = parts[1].split('on')[0].strip()
                        threshold = float(threshold_str)
                        
                        if current_price > threshold:
                            logger.warning(
                                f"{coin} invalidation triggered: price {current_price} "
                                f"above threshold {threshold}"
                            )
                            to_close.append(coin)
                
                except (ValueError, IndexError) as e:
                    logger.error(f"Failed to parse invalidation condition: {invalidation} - {e}")
        
        return to_close

