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
    
    def __init__(self, exchange_client: ExchangeClient, db=None):
        self.exchange = exchange_client
        self.active_orders: Dict[str, List[Dict]] = {}  # coin -> list of orders
        self.db = db  # Database reference for recording trade history
    
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
            
            # Track orders with entry timestamp
            from datetime import datetime
            entry_time = datetime.now()
            
            if coin not in self.active_orders:
                self.active_orders[coin] = []
            
            self.active_orders[coin].extend([
                {'type': 'entry', 'order': entry_order, 'entry_time': entry_time},
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
        position: Dict,
        reason: str = 'manual_close'
    ) -> Dict:
        """
        Close existing position and record trade history.
        
        Args:
            coin: Coin symbol
            symbol: Trading pair
            position: Position info dict
            reason: Reason for closing (manual_close, stop_loss, take_profit, ai_decision)
        
        Returns:
            Close order info
        """
        try:
            quantity = position.get('quantity', 0)
            entry_price = position.get('entry_price', 0)
            
            if quantity == 0:
                logger.warning(f"No position to close for {coin}")
                return {}
            
            # Determine close side (opposite of position)
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
            
            exit_price = close_order.get('average') or close_order.get('price', 0)
            
            logger.info(f"Position closed: {close_order['id']} - {side} {amount} {symbol}")
            
            # Calculate trade details
            from datetime import datetime, timedelta
            
            # Try to get entry_time from active_orders first (most accurate)
            entry_time = None
            if coin in self.active_orders:
                for order_info in self.active_orders[coin]:
                    if order_info['type'] == 'entry' and 'entry_time' in order_info:
                        entry_time = order_info['entry_time']
                        break
            
            # Fallback to position timestamp
            if not entry_time:
                raw_timestamp = position.get('timestamp')
                if raw_timestamp:
                    try:
                        # Handle different timestamp formats
                        if isinstance(raw_timestamp, (int, float)):
                            # Millisecond timestamp
                            entry_time = datetime.fromtimestamp(raw_timestamp / 1000 if raw_timestamp > 1e10 else raw_timestamp)
                        elif isinstance(raw_timestamp, str):
                            entry_time = datetime.fromisoformat(raw_timestamp.replace('Z', '+00:00'))
                        elif isinstance(raw_timestamp, datetime):
                            entry_time = raw_timestamp
                    except Exception as e:
                        logger.warning(f"Failed to parse timestamp {raw_timestamp}: {e}")
                        entry_time = None
            
            close_time = datetime.now()
            
            # Ensure entry_time is datetime or None before calculation
            if entry_time and isinstance(entry_time, datetime):
                duration_minutes = int((close_time - entry_time).total_seconds() / 60)
            else:
                duration_minutes = 0
                entry_time = None  # Ensure it's None for database storage
            
            # Format duration for display
            if duration_minutes > 0:
                hours = duration_minutes // 60
                minutes = duration_minutes % 60
                duration_str = f"{hours}H {minutes}M" if hours > 0 else f"{minutes}M"
            else:
                duration_str = "0M"
            
            # Calculate PnL
            if quantity > 0:  # Long
                pnl = amount * (exit_price - entry_price)
            else:  # Short
                pnl = amount * (entry_price - exit_price)
            
            pnl_percent = (pnl / (entry_price * amount)) * 100 if entry_price * amount > 0 else 0
            
            entry_notional = abs(entry_price * amount)
            exit_notional = abs(exit_price * amount)
            
            # 🚀 获取真实杠杆倍数（增强版）
            leverage = position.get('leverage', 1)
            try:
                # 如果position中没有杠杆或为默认值，尝试从交易所API获取
                if leverage == 1:
                    # 获取当前持仓信息
                    current_positions = await self.exchange.exchange.fetch_positions([symbol])
                    for pos in current_positions:
                        if pos.get('symbol') == symbol and float(pos.get('contracts', 0)) != 0:
                            leverage = int(pos.get('leverage', 1))
                            logger.debug(f"获取到 {coin} 的杠杆倍数: {leverage}x (来源: API持仓查询)")
                            break
                    
                # 如果还是获取不到，尝试从交易所杠杆设置API
                if leverage == 1:
                    try:
                        leverage_info = await self.exchange.exchange.fetch_leverage(symbol)
                        if leverage_info and 'leverage' in leverage_info:
                            leverage = int(leverage_info['leverage'])
                            logger.debug(f"获取到 {coin} 的杠杆倍数: {leverage}x (来源: 杠杆设置API)")
                    except Exception as lev_err:
                        logger.debug(f"获取杠杆设置失败: {lev_err}")
                        
            except Exception as e:
                logger.debug(f"获取 {coin} 杠杆倍数失败，使用position默认值: {e}")
            
            # Record trade history
            # Use close_time as fallback if entry_time is None
            trade_record = {
                'entry_timestamp': entry_time if entry_time else close_time,
                'symbol': symbol,
                'side': 'long' if quantity > 0 else 'short',
                'quantity': amount,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'entry_notional': entry_notional,
                'exit_notional': exit_notional,
                'leverage': leverage,  # 🚀 使用真实杠杆倍数
                'pnl': pnl,
                'pnl_percent': pnl_percent,
                'duration_minutes': duration_minutes,
                'reason': reason
            }
            
            # Save to database if available
            if hasattr(self, 'db') and self.db:
                self.db.save_trade(trade_record)
                logger.info(f"Trade recorded: {coin} P&L={pnl:.2f} ({pnl_percent:.2f}%), Duration: {duration_str}")
            
            # Remove from active orders
            if coin in self.active_orders:
                del self.active_orders[coin]
            
            return {
                'close_order': close_order,
                'trade_record': trade_record
            }
        
        except Exception as e:
            logger.error(f"Failed to close position for {coin}: {e}")
            raise
    
    async def _cancel_pending_orders(self, coin: str, symbol: str):
        """
        Cancel all pending orders for a symbol.
        
        This method:
        1. First tries to cancel tracked orders (from memory)
        2. Then fetches all open orders from exchange and cancels them
        3. Ensures no orphaned orders remain
        """
        cancelled_count = 0
        
        # Method 1: Cancel tracked orders (from memory)
        if coin in self.active_orders:
            for order_info in self.active_orders[coin]:
                if order_info['type'] in ['stop_loss', 'take_profit']:
                    try:
                        order_id = order_info['order']['id']
                        await self.exchange.exchange.cancel_order(order_id, symbol)
                        logger.info(f"✅ Cancelled tracked {order_info['type']} order {order_id}")
                        cancelled_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cancel tracked order {order_id}: {e}")
        
        # Method 2: Fetch and cancel ALL open orders for this symbol from exchange
        # This catches any orders that weren't tracked (e.g., after restart)
        try:
            open_orders = await self.exchange.exchange.fetch_open_orders(symbol)
            
            if open_orders:
                logger.info(f"Found {len(open_orders)} open orders for {symbol}, cancelling all...")
                
                for order in open_orders:
                    try:
                        order_id = order['id']
                        order_type = order.get('type', 'unknown')
                        await self.exchange.exchange.cancel_order(order_id, symbol)
                        logger.info(f"✅ Cancelled open order {order_id} (type: {order_type})")
                        cancelled_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to cancel order {order_id}: {e}")
            
            if cancelled_count > 0:
                logger.info(f"Total cancelled {cancelled_count} orders for {coin}")
        
        except Exception as e:
            logger.warning(f"Failed to fetch open orders for {symbol}: {e}")
    
    async def check_completed_orders(self) -> List[Dict]:
        """
        检查活跃订单中是否有已完成的止盈止损订单
        
        Returns:
            已完成订单的列表，每个订单包含交易信息
        """
        completed_trades = []
        
        # 遍历所有活跃订单
        coins_to_remove = []
        
        for coin, orders in list(self.active_orders.items()):
            try:
                # 查找入场订单信息
                entry_info = None
                sl_order = None
                tp_order = None
                
                for order_info in orders:
                    if order_info['type'] == 'entry':
                        entry_info = order_info
                    elif order_info['type'] == 'stop_loss':
                        sl_order = order_info
                    elif order_info['type'] == 'take_profit':
                        tp_order = order_info
                
                if not entry_info:
                    continue
                
                # 检查止盈止损订单状态
                for order_type, order_info in [('stop_loss', sl_order), ('take_profit', tp_order)]:
                    if not order_info:
                        continue
                        
                    try:
                        order_id = order_info['order']['id']
                        symbol = entry_info['order']['symbol']
                        
                        # 获取订单状态
                        order_status = await self.exchange.exchange.fetch_order(order_id, symbol)
                        
                        if order_status['status'] == 'closed':
                            logger.info(f"🎯 检测到 {order_type} 订单已执行: {order_id} for {coin}")
                            
                            # 🚫 立即取消另一个订单（止盈触发取消止损，止损触发取消止盈）
                            other_order = None
                            if order_type == 'stop_loss' and tp_order:
                                other_order = tp_order
                                other_type = 'take_profit'
                            elif order_type == 'take_profit' and sl_order:
                                other_order = sl_order  
                                other_type = 'stop_loss'
                            
                            if other_order:
                                try:
                                    other_order_id = other_order['order']['id']
                                    await self.exchange.exchange.cancel_order(other_order_id, symbol)
                                    logger.info(f"🚫 已取消对应的 {other_type} 订单: {other_order_id}")
                                except Exception as cancel_err:
                                    logger.warning(f"取消 {other_type} 订单失败: {cancel_err}")
                            
                            # 计算交易信息
                            entry_order = entry_info['order']
                            entry_time = entry_info.get('entry_time', datetime.now())
                            exit_time = datetime.now()
                            
                            # 计算持仓时长
                            if isinstance(entry_time, datetime):
                                holding_duration = exit_time - entry_time
                                duration_minutes = int(holding_duration.total_seconds() / 60)
                            else:
                                duration_minutes = 0
                            
                            # 计算P&L
                            entry_price = float(entry_order.get('price', 0) or entry_order.get('average', 0))
                            exit_price = float(order_status.get('price', 0) or order_status.get('average', 0))
                            quantity = float(entry_order.get('amount', 0))
                            
                            if entry_order['side'] == 'buy':
                                # Long position
                                pnl = (exit_price - entry_price) * quantity
                                side = 'long'
                            else:
                                # Short position  
                                pnl = (entry_price - exit_price) * quantity
                                side = 'short'
                            
                            # 计算收益率
                            investment = entry_price * quantity
                            pnl_percent = (pnl / investment) * 100 if investment > 0 else 0.0
                            
                            # 🚀 获取真实杠杆倍数
                            leverage = 1  # 默认值
                            try:
                                # 方法1: 从交易所获取当前持仓信息中的杠杆
                                positions = await self.exchange.exchange.fetch_positions([symbol])
                                for pos in positions:
                                    if pos.get('symbol') == symbol and float(pos.get('contracts', 0)) != 0:
                                        leverage = int(pos.get('leverage', 1))
                                        logger.debug(f"获取到 {coin} 的杠杆倍数: {leverage}x (来源: 持仓信息)")
                                        break
                                
                                # 方法2: 如果持仓信息获取失败，尝试从订单信息获取
                                if leverage == 1:
                                    # 检查原始订单是否包含杠杆信息
                                    if 'info' in entry_order and entry_order['info']:
                                        order_leverage = entry_order['info'].get('leverage')
                                        if order_leverage:
                                            leverage = int(order_leverage)
                                            logger.debug(f"获取到 {coin} 的杠杆倍数: {leverage}x (来源: 入场订单)")
                                
                                # 方法3: 从交易所API查询杠杆设置
                                if leverage == 1:
                                    try:
                                        leverage_info = await self.exchange.exchange.fetch_leverage(symbol)
                                        if leverage_info and 'leverage' in leverage_info:
                                            leverage = int(leverage_info['leverage'])
                                            logger.debug(f"获取到 {coin} 的杠杆倍数: {leverage}x (来源: API查询)")
                                    except Exception as lev_err:
                                        logger.debug(f"API查询杠杆失败: {lev_err}")
                                
                            except Exception as e:
                                logger.debug(f"获取 {coin} 杠杆倍数失败，使用默认值1: {e}")
                            
                            # 确定关闭原因
                            reason = 'stop_loss' if order_type == 'stop_loss' else 'take_profit'
                            
                            # 记录交易
                            trade_record = {
                                'entry_timestamp': entry_time.isoformat() if isinstance(entry_time, datetime) else str(entry_time),
                                'symbol': coin,
                                'side': side,
                                'quantity': quantity,
                                'entry_price': entry_price,
                                'exit_price': exit_price,
                                'entry_notional': entry_price * quantity,
                                'exit_notional': exit_price * quantity,
                                'leverage': leverage,  # 🚀 使用真实杠杆倍数
                                'pnl': pnl,
                                'pnl_percent': pnl_percent,
                                'duration_minutes': duration_minutes,
                                'reason': reason
                            }
                            
                            # 保存到数据库
                            if hasattr(self, 'db') and self.db:
                                self.db.save_trade(trade_record)
                                
                                duration_str = f"{duration_minutes // 60}h {duration_minutes % 60}m" if duration_minutes >= 60 else f"{duration_minutes}m"
                                logger.info(f"✅ {reason.upper()} 触发记录: {coin} P&L={pnl:.2f} ({pnl_percent:.2f}%), Duration: {duration_str}")
                            
                            completed_trades.append(trade_record)
                            
                            # 标记要移除
                            coins_to_remove.append(coin)
                            break  # 找到一个完成的订单就够了
                            
                    except Exception as e:
                        logger.debug(f"检查订单 {order_id} 状态失败: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"检查 {coin} 的订单状态失败: {e}")
                continue
        
        # 清理已完成的订单
        for coin in coins_to_remove:
            if coin in self.active_orders:
                del self.active_orders[coin]
                logger.debug(f"已清理 {coin} 的活跃订单记录")
        
        return completed_trades
    
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

