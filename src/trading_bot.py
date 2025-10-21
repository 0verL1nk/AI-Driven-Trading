"""Main trading bot orchestrator."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from .config import settings, trading_config
from .data.exchange_client import ExchangeClient
from .data.websocket_client import BinanceWebSocketClient
from .data.indicator_engine import IndicatorEngine
from .ai.prompt_builder import PromptBuilder
from .ai.llm_interface import TradingLLM
from .ai.decision_validator import DecisionValidator
from .execution.order_manager import OrderManager
from .execution.portfolio_manager import PortfolioManager
from .execution.paper_trading import PaperTradingEngine
from .database import TradingDatabase

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot orchestrating the entire AI trading system.
    
    Architecture:
    1. Data Collection: Fetch market data, indicators, funding rates
    2. Prompt Building: Format data for LLM in nof1.ai format
    3. AI Decision: Get trading decisions from LLM
    4. Validation: Validate decisions against risk parameters
    5. Execution: Execute validated trades
    6. Monitoring: Track performance and positions
    """
    
    def __init__(self):
        # Initialize components
        # Always use ExchangeClient for real market data
        self.data_client = ExchangeClient()
        
        if settings.enable_paper_trading:
            logger.info("Running in PAPER TRADING mode")
            paper_balance = trading_config.trading_config['paper_trading']['initial_balance']
            # Use PaperTradingEngine for simulated order execution
            self.exchange = PaperTradingEngine(initial_balance=paper_balance)
        else:
            logger.info("Running in LIVE TRADING mode")
            # Use real ExchangeClient for actual order execution
            self.exchange = self.data_client
        
        self.indicator_engine = IndicatorEngine()
        self.prompt_builder = PromptBuilder()
        
        # 优先使用环境变量的base_url，其次使用配置文件的
        base_url = settings.openai_base_url or trading_config.ai_base_url
        
        self.llm = TradingLLM(
            primary_provider=trading_config.ai_provider,
            model=trading_config.ai_model,
            base_url=base_url
        )
        self.validator = DecisionValidator(trading_config.risk_params)
        self.order_manager = OrderManager(self.exchange)
        
        # Get initial balance
        # For paper trading: use config file
        # For Testnet/Live: will be set from first account fetch
        if settings.enable_paper_trading:
            initial_balance = trading_config.trading_config['paper_trading']['initial_balance']
        else:
            # For live/testnet, will be initialized from real account balance
            initial_balance = None  # Will be set on first fetch
        
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        
        # Initialize database
        self.db = TradingDatabase()
        logger.info("Database initialized for monitoring")
        
        # Initialize WebSocket client for real-time data
        self.ws_client = BinanceWebSocketClient()
        logger.info("WebSocket client initialized for real-time data")
        
        # 缓存最新的市场数据（从WebSocket更新）
        self.latest_prices = {}
        self.latest_klines = {}
        
        self.running = False
        self.decision_interval = trading_config.decision_interval_minutes * 60  # Convert to seconds
        self.price_update_interval = 3  # 价格更新间隔（秒）- 高频更新
    
    async def start(self):
        """Start the trading bot."""
        logger.info("=" * 60)
        logger.info("AI TRADING BOT STARTING")
        logger.info("=" * 60)
        
        self.running = True
        
        # 启动WebSocket数据流（不阻塞）
        symbols = [pair.split('/')[0] + 'USDT' for pair in trading_config.trading_pairs]
        logger.info(f"Starting WebSocket for {len(symbols)} symbols...")
        asyncio.create_task(self.start_websocket_streams(symbols))
        
        # 等待WebSocket连接建立
        await asyncio.sleep(3)
        logger.info("✅ WebSocket streams started")
        
        try:
            # 启动两个并行任务
            await asyncio.gather(
                self.run_price_update_loop(),  # 高频价格更新（每3秒）
                self.run_trading_loop(),        # 低频AI决策（每2.6分钟）
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
            raise  # Re-raise to be handled in main.py
        except asyncio.CancelledError:
            logger.info("Trading loop cancelled")
            raise  # Re-raise to be handled in main.py
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
            await self.shutdown()
            raise
    
    async def start_websocket_streams(self, symbols: List[str]):
        """启动WebSocket数据流"""
        async def on_kline(symbol: str, kline_data: Dict):
            """K线数据回调"""
            if kline_data['is_closed']:  # 只处理已完成的K线
                self.latest_klines[symbol] = kline_data
                logger.debug(f"Updated kline for {symbol}: ${kline_data['close']:.2f}")
        
        async def on_ticker(symbol: str, ticker_data: Dict):
            """Ticker数据回调"""
            # 只存储价格值，不存储整个字典
            self.latest_prices[symbol] = float(ticker_data.get('price', ticker_data.get('last', 0)))
            logger.debug(f"Updated price for {symbol}: ${self.latest_prices[symbol]:.2f}")
        
        # 启动K线和Ticker流（并行）
        await asyncio.gather(
            self.ws_client.subscribe_klines(symbols, '3m', on_kline),
            self.ws_client.subscribe_ticker(symbols, on_ticker)
        )
    
    async def run_price_update_loop(self):
        """高频价格更新循环 - 每3秒更新一次数据库（供前端显示）"""
        logger.info("🔄 Starting high-frequency price update loop (every 3s)")
        
        while self.running:
            try:
                # 从缓存的WebSocket数据更新数据库
                if self.latest_prices:
                    for symbol, price in self.latest_prices.items():
                        # 从symbol提取coin名称（如BTCUSDT -> BTC）
                        coin = symbol.replace('USDT', '').replace('usdt', '')
                        
                        # 获取额外的市场数据（如果有）
                        price_data = {
                            'price': float(price),
                            'rsi_14': 0,  # 暂时使用0，完整数据在AI循环中更新
                            'macd': 0,
                            'funding_rate': 0,
                            'open_interest': 0
                        }
                        
                        # 保存到数据库供前端查询
                        self.db.save_coin_price(coin, price_data)
                    
                    logger.debug(f"💾 Updated prices for {len(self.latest_prices)} coins")
                
                # 等待3秒
                await asyncio.sleep(self.price_update_interval)
                
            except Exception as e:
                logger.error(f"Error in price update loop: {e}")
                await asyncio.sleep(self.price_update_interval)
    
    async def fetch_positions_with_retry(self, max_retries=2):
        """
        Fetch positions with retry logic to handle API data anomalies.
        Uses exponential backoff to avoid IP bans.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 2, total 3 tries)
            
        Returns:
            List of positions
        """
        for attempt in range(max_retries + 1):
            try:
                positions = await self.exchange.fetch_positions()
                
                # Validate data quality
                has_invalid_data = False
                for pos in positions:
                    # Check for None values in critical fields (only if position exists)
                    contracts = pos.get('contracts', 0)
                    if contracts and contracts != 0:
                        critical_fields = ['entryPrice', 'markPrice', 'unrealizedPnl']
                        for field in critical_fields:
                            if pos.get(field) is None:
                                has_invalid_data = True
                                logger.warning(f"Invalid data in position {pos.get('symbol')}: {field} is None")
                                break
                    if has_invalid_data:
                        break
                
                # If data is valid, return it
                if not has_invalid_data:
                    if attempt > 0:
                        logger.info(f"✅ Successfully fetched valid position data on attempt {attempt + 1}")
                    return positions
                
                # If invalid, retry with exponential backoff
                if attempt < max_retries:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = 5 * (2 ** attempt)
                    logger.warning(
                        f"⚠️ Invalid data detected. Retrying in {wait_time}s "
                        f"(attempt {attempt + 2}/{max_retries + 1})... "
                        f"[Exponential backoff to avoid rate limit]"
                    )
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                error_msg = str(e)
                # Check if it's a rate limit error
                is_rate_limit = '418' in error_msg or 'rate limit' in error_msg.lower()
                
                if is_rate_limit:
                    logger.error(f"🚫 Rate limit hit! Waiting 60s before retry...")
                    if attempt < max_retries:
                        await asyncio.sleep(60)  # Wait 1 minute for rate limit
                else:
                    logger.error(f"Error fetching positions (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        wait_time = 5 * (2 ** attempt)
                        logger.warning(f"Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
        
        # If all retries failed, use safe fallback with empty positions
        logger.error("❌ All position fetch attempts failed, returning empty positions as fallback")
        logger.warning("⚠️ System will continue with no positions. This is safe but may miss existing trades.")
        return []
    
    async def run_trading_loop(self):
        """Main trading loop."""
        iteration = 0
        
        while self.running:
            iteration += 1
            logger.info(f"\n{'=' * 60}")
            logger.info(f"TRADING ITERATION #{iteration}")
            logger.info(f"{'=' * 60}\n")
            
            try:
                # Step 1: Collect market data
                logger.info("Step 1: Collecting market data...")
                market_data = await self.collect_market_data()
                
                # Step 2: Get current account state
                logger.info("Step 2: Fetching account state...")
                balance = await self.exchange.fetch_balance()
                positions = await self.fetch_positions_with_retry(max_retries=3)
                
                account_state = self.portfolio.calculate_account_state(balance, positions)
                formatted_positions = self.portfolio.format_positions_for_prompt(positions)
                
                logger.info(f"Account Value: ${account_state['total_value']:.2f}")
                logger.info(f"Return: {account_state['total_return']:.2f}%")
                logger.info(f"Positions: {account_state['num_positions']}")
                
                # Save account state to database
                self.db.save_account_state(account_state)
                
                # Save market prices to database (for frontend display)
                current_prices = {}
                for coin, data in market_data.items():
                    latest = data['intraday_df'].iloc[-1]
                    price_data = {
                        'price': float(latest['close']),
                        'rsi_14': float(latest.get('rsi_14', 0)),
                        'macd': float(latest.get('macd', 0)),
                        'funding_rate': float(data.get('funding_rate', 0)),
                        'open_interest': float(data.get('open_interest', 0))
                    }
                    self.db.save_coin_price(coin, price_data)
                    current_prices[coin] = price_data['price']
                
                # Step 3: Check invalidation conditions
                logger.info("Step 3: Checking invalidation conditions...")
                
                to_invalidate = await self.order_manager.check_invalidation_conditions(
                    formatted_positions,
                    current_prices
                )
                
                # Close invalidated positions
                for coin in to_invalidate:
                    symbol = f"{coin}/USDT:USDT"
                    pos = next((p for p in formatted_positions if p['symbol'] == coin), None)
                    if pos:
                        logger.warning(f"Closing {coin} due to invalidation")
                        await self.order_manager.execute_close(coin, symbol, pos)
                
                # Step 4: Build prompt for LLM
                logger.info("Step 4: Building AI prompt...")
                prompt = self.prompt_builder.build_trading_prompt(
                    market_data=market_data,
                    account_state=account_state,
                    positions=formatted_positions
                )
                
                # Log prompt size
                logger.info(f"Prompt size: {len(prompt)} characters")
                
                # Step 5: Get AI decision
                logger.info("Step 5: Requesting AI decision...")
                # Get all configured LLM parameters (temperature, max_tokens, stream, thinking_budget, etc.)
                generation_kwargs = trading_config.get_ai_generation_kwargs()
                llm_result = await self.llm.decide(prompt, **generation_kwargs)
                
                # Extract decisions and thinking from result
                decisions = llm_result.get('decisions', {})
                thinking = llm_result.get('thinking', '')
                
                if thinking:
                    logger.info(f"💭 AI Thinking: {thinking[:200]}..." if len(thinking) > 200 else f"💭 AI Thinking: {thinking}")
                
                logger.info(f"Received decisions for {len(decisions)} coins")
                
                # Step 6: Validate decisions
                logger.info("Step 6: Validating decisions...")
                
                # Check if decisions is valid
                if not isinstance(decisions, dict):
                    logger.error(f"Invalid decisions format: expected dict, got {type(decisions)}")
                    logger.error(f"Decisions content: {str(decisions)[:500]}")
                    decisions = {}
                
                # Filter out invalid entries (non-dict values)
                valid_decisions = {}
                for coin, decision in decisions.items():
                    if isinstance(decision, dict):
                        valid_decisions[coin] = decision
                    else:
                        logger.warning(f"Skipping {coin}: decision is {type(decision)}, not dict")
                
                validated_decisions = self.validator.validate_all_decisions(
                    valid_decisions,
                    current_prices,
                    account_state['total_value']
                )
                
                logger.info(f"Validated {len(validated_decisions)}/{len(valid_decisions)} decisions")
                
                # Save ONLY validated decisions to database (with thinking)
                # Invalid decisions are not saved to keep the database clean
                for coin, decision in validated_decisions.items():
                    try:
                        self.db.save_ai_decision(coin, decision, thinking)
                    except Exception as e:
                        logger.error(f"Failed to save decision for {coin}: {e}")
                
                # Log rejected decisions for debugging
                rejected_coins = set(valid_decisions.keys()) - set(validated_decisions.keys())
                if rejected_coins:
                    logger.info(f"ℹ️  Rejected decisions (not saved to DB): {', '.join(rejected_coins)}")
                
                # Step 7: Execute trades
                logger.info("Step 7: Executing trades...")
                execution_summary = await self.execute_decisions(validated_decisions, formatted_positions, current_prices)
                
                # Log execution summary
                total_actions = sum(execution_summary.values())
                if total_actions > 0:
                    logger.info(f"✅ Execution Summary: "
                              f"{execution_summary['entries']} entries, "
                              f"{execution_summary['closes']} closes, "
                              f"{execution_summary['holds']} holds, "
                              f"{execution_summary['no_actions']} no-actions")
                else:
                    logger.info("ℹ️  No trades executed this cycle")
                
                # Step 8: Log performance
                performance = self.portfolio.get_performance_metrics()
                if performance:
                    logger.info(f"\nPerformance Summary:")
                    logger.info(f"  Current Positions: {len(formatted_positions)}")  # 当前持仓数
                    logger.info(f"  Completed Trades: {performance['total_trades']}")  # 已完成交易数
                    logger.info(f"  Win Rate: {performance['win_rate']:.1f}%")
                    logger.info(f"  Total PnL: ${performance['total_pnl']:.2f}")
                    logger.info(f"  Max Drawdown: {performance['max_drawdown']:.2f}%")
                
            except Exception as e:
                logger.error(f"Error in trading iteration: {e}", exc_info=True)
            
            # Wait for next iteration
            logger.info(f"\nWaiting {self.decision_interval:.0f} seconds until next iteration...")
            await asyncio.sleep(self.decision_interval)
    
    async def collect_market_data(self) -> Dict[str, Dict]:
        """
        Collect all market data for all trading pairs.
        
        Returns:
            Dict with coin -> market data
        """
        market_data = {}
        
        for pair in trading_config.trading_pairs:
            coin = pair.split('/')[0]  # Extract 'BTC' from 'BTC/USDT:USDT'
            
            try:
                # 使用CCXT获取历史数据（更稳定）
                # WebSocket用于实时价格更新，不用于历史数据
                intraday_df = await self.data_client.fetch_ohlcv(
                    symbol=pair,
                    timeframe='3m',
                    limit=100
                )
                
                if intraday_df.empty:
                    logger.warning(f"No data for {coin}, skipping")
                    continue
                
                # Add indicators
                intraday_df = self.indicator_engine.add_all_indicators(intraday_df)
                
                # Fetch 4-hour longer-term data
                longterm_df = await self.data_client.fetch_ohlcv(
                    symbol=pair,
                    timeframe='4h',
                    limit=100
                )
                
                if longterm_df.empty:
                    logger.warning(f"No longterm data for {coin}, skipping")
                    continue
                
                # Add indicators to long-term data
                longterm_df = self.indicator_engine.add_all_indicators(longterm_df)
                
                # Fetch funding rate and open interest from data client
                funding_data = await self.data_client.fetch_funding_rate(pair)
                oi_data = await self.data_client.fetch_open_interest(pair)
                
                # Calculate OI average (last 24 hours approximation)
                oi_average = oi_data.get('open_interest', 0) * 0.98  # Placeholder
                
                market_data[coin] = {
                    'intraday_df': intraday_df,
                    'longterm_df': longterm_df,
                    'funding_rate': funding_data.get('funding_rate', 0),
                    'open_interest': oi_data.get('open_interest', 0),
                    'oi_average': oi_average
                }
                
                # Save price data to database
                latest = intraday_df.iloc[-1]
                self.db.save_coin_price(coin, {
                    'price': latest['close'],
                    'rsi_14': latest.get('rsi_14', 0),
                    'macd': latest.get('macd', 0),
                    'funding_rate': funding_data.get('funding_rate', 0),
                    'open_interest': oi_data.get('open_interest', 0)
                })
                
                logger.debug(f"Collected data for {coin}")
            
            except Exception as e:
                logger.error(f"Failed to collect data for {coin}: {e}")
        
        return market_data
    
    async def execute_decisions(
        self,
        decisions: Dict[str, Dict],
        current_positions: List[Dict],
        current_prices: Dict[str, float]
    ) -> Dict[str, int]:
        """
        Execute validated trading decisions.
        
        Returns:
            Dict with execution summary: {'entries': int, 'closes': int, 'holds': int, 'no_actions': int}
        """
        position_map = {pos['symbol']: pos for pos in current_positions}
        
        # Track execution summary
        summary = {'entries': 0, 'closes': 0, 'holds': 0, 'no_actions': 0}
        
        for coin, decision in decisions.items():
            if 'trade_signal_args' not in decision:
                continue
            
            args = decision['trade_signal_args']
            signal = args.get('signal')
            symbol = f"{coin}/USDT:USDT"
            
            try:
                if signal == 'entry':
                    # Open new position
                    await self.execute_entry(coin, symbol, args, current_prices[coin])
                    summary['entries'] += 1
                
                elif signal == 'close_position':
                    # Close existing position
                    if coin in position_map:
                        await self.order_manager.execute_close(
                            coin,
                            symbol,
                            position_map[coin]
                        )
                        summary['closes'] += 1
                        logger.info(f"Closed position for {coin}")
                    else:
                        logger.warning(f"Cannot close {coin}: no existing position")
                
                elif signal == 'hold':
                    summary['holds'] += 1
                    logger.debug(f"Holding position for {coin}")
                
                elif signal == 'no_action':
                    summary['no_actions'] += 1
                    logger.debug(f"No action for {coin}")
                
            except Exception as e:
                logger.error(f"Failed to execute {signal} for {coin}: {e}")
        
        return summary
    
    async def execute_entry(
        self,
        coin: str,
        symbol: str,
        args: Dict,
        current_price: float
    ):
        """Execute entry order."""
        leverage = args.get('leverage', 10)
        stop_loss = args.get('stop_loss')
        take_profit = args.get('profit_target')
        risk_usd = args.get('risk_usd')
        
        # Get account value for margin check
        account_value = self.portfolio.get_total_value()
        
        # Calculate position size with margin constraint
        position_size = self.validator.calculate_position_size(
            risk_usd=risk_usd,
            entry_price=current_price,
            stop_loss=stop_loss,
            leverage=leverage,
            account_value=account_value
        )
        
        if position_size == 0:
            logger.warning(f"Position size is zero for {coin}, skipping entry")
            return
        
        # Determine side (long or short)
        if take_profit > current_price:
            side = 'buy'  # Long
        else:
            side = 'sell'  # Short
        
        logger.info(f"Entering {side.upper()} position for {coin}:")
        logger.info(f"  Size: {position_size:.4f}")
        logger.info(f"  Leverage: {leverage}x")
        logger.info(f"  Entry: {current_price}")
        logger.info(f"  Stop Loss: {stop_loss}")
        logger.info(f"  Take Profit: {take_profit}")
        logger.info(f"  Risk: ${risk_usd:.2f}")
        
        # Execute entry with SL/TP
        result = await self.order_manager.execute_entry(
            coin=coin,
            symbol=symbol,
            side=side,
            quantity=position_size,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        # Record trade
        self.portfolio.record_trade(
            coin=coin,
            action='entry_' + side,
            quantity=position_size,
            price=current_price
        )
        
        logger.info(f"Successfully entered {coin} position")
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down trading bot...")
        self.running = False
        
        # Close all positions (optional, comment out if you want to keep positions)
        # positions = await self.exchange.fetch_positions()
        # for pos in positions:
        #     symbol = pos['symbol']
        #     coin = symbol.split('/')[0]
        #     await self.order_manager.execute_close(coin, symbol, pos)
        
        # 停止WebSocket（现在是异步的）
        if hasattr(self, 'ws_client'):
            try:
                await self.ws_client.stop()
                logger.debug("WebSocket client stopped")
            except Exception as e:
                logger.debug(f"Error stopping WebSocket client: {e}")
        
        # Close exchange connections
        try:
            if hasattr(self.data_client, 'exchange'):
                await self.data_client.exchange.close()
                logger.debug("Data client connection closed")
        except Exception as e:
            logger.debug(f"Error closing data client: {e}")
        
        # Close exchange if it's different from data_client
        if self.exchange != self.data_client:
            try:
                if hasattr(self.exchange, 'close'):
                    await self.exchange.close()
                    logger.debug("Exchange connection closed")
            except Exception as e:
                logger.debug(f"Error closing exchange: {e}")
        
        logger.info("✅ Shutdown complete")

