"""Main trading bot orchestrator."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

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
    
    def __init__(self, db_type: Optional[str] = None, **db_kwargs):
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
            base_url=base_url,
            is_reasoning_model=trading_config.is_reasoning_model
        )
        self.validator = DecisionValidator(trading_config.risk_params)
        
        # Initialize database first (needed by PortfolioManager for persistence)
        # Use settings from environment variables (via Settings object)
        # Priority: constructor parameter > settings > defaults
        
        resolved_db_type = db_type if db_type else settings.db_type
        resolved_db_kwargs = db_kwargs.copy() if db_kwargs else {}
        
        if resolved_db_type == 'sqlite':
            resolved_db_kwargs['db_path'] = resolved_db_kwargs.get('db_path', 'trading_data.db')
        elif resolved_db_type == 'mysql':
            # Use settings if not provided via kwargs
            resolved_db_kwargs['host'] = resolved_db_kwargs.get('host') or settings.db_host or 'localhost'
            resolved_db_kwargs['port'] = resolved_db_kwargs.get('port') or settings.db_port or 3306
            resolved_db_kwargs['user'] = resolved_db_kwargs.get('user') or settings.db_user or 'root'
            resolved_db_kwargs['password'] = resolved_db_kwargs.get('password') or settings.db_password or ''
            resolved_db_kwargs['database'] = resolved_db_kwargs.get('database') or settings.db_name or 'trading_db'
            # SSL configuration
            resolved_db_kwargs['ssl_mode'] = resolved_db_kwargs.get('ssl_mode') or settings.db_ssl_mode or 'REQUIRED'
            resolved_db_kwargs['ssl_ca'] = resolved_db_kwargs.get('ssl_ca') or settings.db_ssl_ca
        
        self.db = TradingDatabase(db_type=resolved_db_type, **resolved_db_kwargs)
        logger.info(f"Database initialized ({resolved_db_type.upper()}) for monitoring")
        
        self.order_manager = OrderManager(self.exchange, db=self.db)
        
        # Get initial balance
        # For paper trading: use config file
        # For Testnet/Live: will be set from first account fetch
        if settings.enable_paper_trading:
            initial_balance = trading_config.trading_config['paper_trading']['initial_balance']
        else:
            # For live/testnet, will be initialized from real account balance
            initial_balance = None  # Will be set on first fetch
        
        self.portfolio = PortfolioManager(initial_balance=initial_balance, db=self.db)
        
        # Initialize WebSocket client for real-time data
        self.ws_client = BinanceWebSocketClient()
        logger.info("WebSocket client initialized for real-time data")
        
        # 缓存最新的市场数据（从WebSocket更新）
        self.latest_prices = {}
        self.latest_klines = {}
        
        self.running = False
        self.decision_interval = trading_config.decision_interval_minutes * 60  # Convert to seconds
        self.price_update_interval = 3  # 价格更新间隔（秒）- 高频更新
    
    async def start(self, shutdown_event: Optional[asyncio.Event] = None):
        """
        Start the trading bot.
        
        Args:
            shutdown_event: Optional asyncio.Event for graceful shutdown (decoupled)
        """
        logger.info("=" * 60)
        logger.info("AI TRADING BOT STARTING")
        logger.info("=" * 60)
        
        self.running = True
        self.shutdown_event = shutdown_event
        
        # Start monitoring shutdown event if provided
        if shutdown_event:
            monitor_task = asyncio.create_task(self._monitor_shutdown_event())
        
        # 启动WebSocket数据流（不阻塞）
        symbols = [pair.split('/')[0] + 'USDT' for pair in trading_config.trading_pairs]
        logger.info(f"Starting WebSocket for {len(symbols)} symbols...")
        ws_task = asyncio.create_task(self.start_websocket_streams(symbols))
        
        # 等待WebSocket连接建立
        await asyncio.sleep(3)
        logger.info("✅ WebSocket streams started")
        
        # 创建主循环任务
        price_update_task = asyncio.create_task(self.run_price_update_loop())
        trading_loop_task = asyncio.create_task(self.run_trading_loop())
        
        try:
            # 等待所有任务完成（或直到 self.running 变为 False）
            tasks = [price_update_task, trading_loop_task, ws_task]
            if shutdown_event:
                tasks.append(monitor_task)
            
            # 使用 asyncio.wait 等待任务，同时检查 running 标志和 shutdown_event
            while self.running:
                # 检查 shutdown_event 是否被设置（快速响应）
                if shutdown_event and shutdown_event.is_set():
                    logger.info("🛑 Shutdown event detected, stopping all tasks...")
                    self.running = False
                    break
                
                done, pending = await asyncio.wait(
                    tasks,
                    timeout=0.5,  # 更频繁检查
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 再次检查 shutdown_event（可能在等待期间被设置）
                if shutdown_event and shutdown_event.is_set():
                    logger.info("🛑 Shutdown event detected during wait, stopping all tasks...")
                    self.running = False
                    break
                
                # 如果收到停止信号，取消所有任务
                if not self.running:
                    logger.info("🛑 Stopping all tasks...")
                    for task in pending:
                        if not task.done():
                            task.cancel()
                    break
                
                # 检查是否有任务异常
                for task in done:
                    if task.exception():
                        raise task.exception()
            
            # 取消所有任务
            logger.info("🛑 Cancelling all tasks...")
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # 等待所有任务完成或取消
            logger.info("⏳ Waiting for tasks to complete...")
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except KeyboardInterrupt:
            logger.info("⚠️  Keyboard interrupt received in start()")
            self.running = False
            # 取消所有任务
            all_tasks = [price_update_task, trading_loop_task, ws_task]
            if shutdown_event:
                all_tasks.append(monitor_task)
            for task in all_tasks:
                if not task.done():
                    task.cancel()
            # 等待任务取消完成
            await asyncio.gather(*all_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            logger.info("⚠️  Tasks cancelled in start()")
            self.running = False
        except Exception as e:
            logger.error(f"❌ Fatal error in trading loop: {e}", exc_info=True)
            self.running = False
            # 取消所有任务
            all_tasks = [price_update_task, trading_loop_task, ws_task]
            if shutdown_event:
                all_tasks.append(monitor_task)
            for task in all_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*all_tasks, return_exceptions=True)
            raise
        finally:
            # 确保所有任务都停止
            self.running = False
            logger.info("🛑 All tasks stopped")
            # 调用 shutdown 确保清理
            await self.shutdown()
    
    async def start_websocket_streams(self, symbols: List[str]):
        """启动WebSocket数据流"""
        async def on_kline(symbol: str, kline_data: Dict):
            """K线数据回调"""
            if kline_data['is_closed']:  # 只处理已完成的K线
                self.latest_klines[symbol] = kline_data
        
        async def on_ticker(symbol: str, ticker_data: Dict):
            """Ticker数据回调"""
            # 只存储价格值，不存储整个字典
            self.latest_prices[symbol] = float(ticker_data.get('price', ticker_data.get('last', 0)))
        
        try:
            # 启动K线和Ticker流（并行）
            await asyncio.gather(
                self.ws_client.subscribe_klines(symbols, '3m', on_kline),
                self.ws_client.subscribe_ticker(symbols, on_ticker)
            )
        except asyncio.CancelledError:
            logger.info("🛑 WebSocket streams cancelled")
            raise
    
    async def run_price_update_loop(self):
        """高频价格更新循环 - 每3秒更新一次数据库（供前端显示）"""
        logger.info("🔄 Price update loop started (every 3s)")
        
        try:
            while self.running:
                await self._update_price_data()
                await self._update_account_state()
                await self._check_completed_orders()
                
                if not self.running:
                    break
                    
                await self._sleep_with_check(self.price_update_interval)
        except asyncio.CancelledError:
            logger.info("🛑 Price update loop cancelled")
            raise
    
    async def _update_price_data(self):
        """更新价格数据到数据库（解耦）"""
        if not self.latest_prices:
            return
        
        for symbol, price in self.latest_prices.items():
            coin = symbol.replace('USDT', '').replace('usdt', '')
            price_data = {
                'price': float(price),
                'rsi_14': 0,
                'macd': 0,
                'funding_rate': 0,
                'open_interest': 0
            }
            self.db.save_coin_price(coin, price_data)
    
    async def _update_account_state(self):
        """更新账户状态（解耦，独立错误处理）"""
        try:
            balance = await self.exchange.fetch_balance()
            positions = await self.exchange.fetch_positions()
            
            realtime_prices = {}
            for symbol, price in self.latest_prices.items():
                if symbol.endswith('USDT'):
                    base = symbol[:-4]
                    realtime_prices[f"{base}/USDT:USDT"] = price
            
            account_state = self.portfolio.calculate_account_state(
                balance, positions, realtime_prices=realtime_prices
            )
            self.db.save_account_state(account_state)
            self.db._save_positions_to_db(positions, realtime_prices)
        except Exception as e:
            if "rate limit" in str(e).lower() or "timeout" in str(e).lower():
                logger.warning(f"Account state update issue: {e}")
    
    async def _check_completed_orders(self):
        """检查已完成的订单（解耦，独立错误处理）"""
        try:
            completed_trades = await self.order_manager.check_completed_orders()
            if completed_trades:
                logger.info(f"📈 {len(completed_trades)} order(s) completed")
                for trade in completed_trades:
                    reason = trade.get('reason', 'unknown')
                    pnl = trade.get('pnl', 0)
                    symbol = trade.get('symbol', 'unknown')
                    logger.info(f"   {symbol}: {reason}, P&L=${pnl:.2f}")
        except Exception:
            pass
    
    async def _sleep_with_check(self, seconds: float):
        """带 running 检查的 sleep（解耦）"""
        elapsed = 0
        check_interval = 0.1  # 每100ms检查一次
        while elapsed < seconds and self.running:
            await asyncio.sleep(min(check_interval, seconds - elapsed))
            elapsed += check_interval
            if not self.running:
                break
    
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
            if not self.running:
                return []
                
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
                    await self._sleep_with_check(wait_time)
                    
            except Exception as e:
                if not self.running:
                    return []
                    
                error_msg = str(e)
                # Check if it's a rate limit error
                is_rate_limit = '418' in error_msg or 'rate limit' in error_msg.lower()
                
                if is_rate_limit:
                    logger.error(f"🚫 Rate limit hit! Waiting 60s before retry...")
                    if attempt < max_retries:
                        await self._sleep_with_check(60)  # 使用可中断的 sleep
                else:
                    logger.error(f"Error fetching positions (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    if attempt < max_retries:
                        wait_time = 5 * (2 ** attempt)
                        logger.warning(f"Retrying in {wait_time}s...")
                        await self._sleep_with_check(wait_time)  # 使用可中断的 sleep
        
        # If all retries failed, use safe fallback with empty positions
        logger.error("❌ All position fetch attempts failed, returning empty positions as fallback")
        logger.warning("⚠️ System will continue with no positions. This is safe but may miss existing trades.")
        return []
    
    async def run_trading_loop(self):
        """Main trading loop."""
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                logger.info(f"\n{'=' * 60}")
                logger.info(f"ITERATION #{iteration}")
                logger.info(f"{'=' * 60}")
                
                try:
                    await self._run_trading_iteration()
                except Exception as e:
                    logger.error(f"❌ Error in trading iteration: {e}", exc_info=True)
                
                if not self.running:
                    break
                    
                logger.info(f"⏳ Next iteration in {self.decision_interval:.0f}s...\n")
                await self._sleep_with_check(self.decision_interval)
        except asyncio.CancelledError:
            logger.info("🛑 Trading loop cancelled")
            raise
    
    async def _run_trading_iteration(self):
        """执行一次交易迭代（解耦，减少缩进）"""
        # Step 1: Collect market data
        market_data = await self.collect_market_data()
        if not self.running:
            return
        
        # Step 2: Get current account state
        balance = await self.exchange.fetch_balance()
        if not self.running:
            return
            
        positions = await self.fetch_positions_with_retry(max_retries=3)
        if not self.running:
            return
        
        realtime_prices = self._convert_to_realtime_prices()
        account_state = self.portfolio.calculate_account_state(
            balance, positions, realtime_prices=realtime_prices
        )
        formatted_positions = self.portfolio.format_positions_for_prompt(positions)
        
        logger.info(f"Account: ${account_state['total_value']:.2f} | "
                  f"Return: {account_state['total_return']:.2f}% | "
                  f"Positions: {account_state['num_positions']}")
        
        self.db.save_account_state(account_state)
        current_prices = self._save_market_prices(market_data)
        
        # Step 3: Check invalidation conditions
        await self._handle_invalidated_positions(formatted_positions, current_prices)
        if not self.running:
            return
        
        # Step 4: Build prompt and get AI decision
        prompt = self.prompt_builder.build_trading_prompt(
            market_data=market_data,
            account_state=account_state,
            positions=formatted_positions
        )
        
        # Get system prompt with format requirements
        system_prompt = self.prompt_builder.get_system_prompt()
        
        generation_kwargs = trading_config.get_ai_generation_kwargs()
        generation_kwargs['system'] = system_prompt  # Add system prompt
        
        llm_result = await self.llm.decide(prompt, **generation_kwargs)
        if not self.running:
            return
        
        decisions, thinking = self._extract_decisions(llm_result)
        validated_decisions = self._validate_decisions(
            decisions, current_prices, account_state['total_value']
        )
        
        # Step 5: Execute trades
        execution_summary = await self.execute_decisions(
            validated_decisions, formatted_positions, current_prices, thinking
        )
        if not self.running:
            return
        
        self._log_execution_summary(execution_summary)
        self._log_performance_summary()
    
    def _convert_to_realtime_prices(self) -> Dict[str, float]:
        """转换价格格式（解耦）"""
        realtime_prices = {}
        for symbol, price in self.latest_prices.items():
            if symbol.endswith('USDT'):
                base = symbol[:-4]
                realtime_prices[f"{base}/USDT:USDT"] = price
        return realtime_prices
    
    def _save_market_prices(self, market_data: Dict) -> Dict[str, float]:
        """保存市场价格并返回当前价格字典（解耦）"""
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
        return current_prices
    
    async def _handle_invalidated_positions(self, formatted_positions: List[Dict], current_prices: Dict[str, float]):
        """处理失效的持仓（解耦）"""
        to_invalidate = await self.order_manager.check_invalidation_conditions(
            formatted_positions, current_prices
        )
        
        for coin in to_invalidate:
            symbol = f"{coin}/USDT:USDT"
            pos = next((p for p in formatted_positions if p['symbol'] == coin), None)
            if pos:
                logger.warning(f"⚠️  Closing {coin} (invalidation triggered)")
                await self.order_manager.execute_close(coin, symbol, pos)
    
    def _extract_decisions(self, llm_result: Dict) -> tuple:
        """提取决策和思考过程（解耦）"""
        decisions = llm_result.get('decisions', {})
        thinking = llm_result.get('thinking', '')
        
        if thinking and len(thinking) > 0:
            preview = thinking[:150] + "..." if len(thinking) > 150 else thinking
            logger.info(f"💭 AI Thinking: {preview}")
        
        if not isinstance(decisions, dict):
            logger.error(f"❌ Invalid decisions format: expected dict, got {type(decisions)}")
            decisions = {}
        
        return decisions, thinking
    
    def _validate_decisions(self, decisions: Dict, current_prices: Dict[str, float], total_value: float) -> Dict:
        """验证决策（解耦）"""
        valid_decisions = {}
        for coin, decision in decisions.items():
            if isinstance(decision, dict):
                valid_decisions[coin] = decision
            else:
                logger.warning(f"Skipping {coin}: invalid decision format")
        
        validated_decisions = self.validator.validate_all_decisions(
            valid_decisions, current_prices, total_value
        )
        
        rejected_coins = set(valid_decisions.keys()) - set(validated_decisions.keys())
        if rejected_coins:
            logger.warning(f"⚠️  Rejected decisions: {', '.join(rejected_coins)}")
        
        return validated_decisions
    
    def _log_execution_summary(self, execution_summary: Dict):
        """记录执行摘要（解耦）"""
        total_actions = sum(execution_summary.values())
        if total_actions > 0:
            actions = []
            if execution_summary['entries'] > 0:
                actions.append(f"{execution_summary['entries']} entries")
            if execution_summary['closes'] > 0:
                actions.append(f"{execution_summary['closes']} closes")
            if execution_summary['holds'] > 0:
                actions.append(f"{execution_summary['holds']} holds")
            logger.info(f"✅ Actions: {', '.join(actions)}")
    
    def _log_performance_summary(self):
        """记录性能摘要（解耦）"""
        performance = self.portfolio.get_performance_metrics()
        if performance and performance['total_trades'] > 0:
            logger.info(f"📊 Performance: "
                      f"{performance['total_trades']} trades | "
                      f"Win Rate: {performance['win_rate']:.1f}% | "
                      f"PnL: ${performance['total_pnl']:.2f} | "
                      f"DD: {performance['max_drawdown']:.2f}%")
    
    async def collect_market_data(self) -> Dict[str, Dict]:
        """
        Collect all market data for all trading pairs.
        
        Returns:
            Dict with coin -> market data
        """
        market_data = {}
        
        for pair in trading_config.trading_pairs:
            # 检查是否需要停止
            if not self.running:
                return market_data
                
            coin = pair.split('/')[0]  # Extract 'BTC' from 'BTC/USDT:USDT'
            
            try:
                # 使用CCXT获取历史数据（更稳定）
                # WebSocket用于实时价格更新，不用于历史数据
                intraday_df = await self.data_client.fetch_ohlcv(
                    symbol=pair,
                    timeframe='3m',
                    limit=100
                )
                
                if not self.running:
                    return market_data
                
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
                
                if not self.running:
                    return market_data
                
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
                
                # Data collected silently
            
            except Exception as e:
                logger.error(f"Failed to collect data for {coin}: {e}")
        
        return market_data
    
    async def execute_decisions(
        self,
        decisions: Dict[str, Dict],
        current_positions: List[Dict],
        current_prices: Dict[str, float],
        thinking: str = ""
    ) -> Dict[str, int]:
        """
        Execute validated trading decisions and save successful ones to database.
        
        Args:
            decisions: Validated trading decisions
            current_positions: Current portfolio positions
            current_prices: Current market prices
            thinking: AI thinking process to save with successful decisions
        
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
                execution_success = False
                
                if signal == 'entry':
                    # Open new position
                    await self.execute_entry(coin, symbol, args, current_prices[coin])
                    summary['entries'] += 1
                    execution_success = True
                    logger.info(f"✅ Successfully opened position for {coin}")
                
                elif signal == 'close_position':
                    # Close existing position
                    if coin in position_map:
                        # 🆕 Log price change since AI decision
                        decision_price = current_prices[coin]
                        realtime_price = self.latest_prices.get(f"{coin}USDT", decision_price)
                        if realtime_price != decision_price:
                            price_change_pct = (realtime_price - decision_price) / decision_price * 100
                            logger.info(
                                f"💱 Price changed {price_change_pct:+.2f}% during AI decision "
                                f"({decision_price:.4f} → {realtime_price:.4f})"
                            )
                        
                        await self.order_manager.execute_close(
                            coin,
                            symbol,
                            position_map[coin]
                        )
                        summary['closes'] += 1
                        execution_success = True
                        logger.info(f"✅ Successfully closed position for {coin}")
                    else:
                        logger.warning(f"Cannot close {coin}: no existing position")
                
                elif signal == 'hold':
                    summary['holds'] += 1
                    execution_success = True
                
                elif signal == 'no_action':
                    summary['no_actions'] += 1
                    execution_success = True
                
                # 🆕 只有交易成功执行后才保存AI决策到数据库
                if execution_success:
                    try:
                        self.db.save_ai_decision(coin, decision, thinking)
                        # Decision saved silently
                    except Exception as e:
                        logger.error(f"Failed to save decision for {coin}: {e}")
                
            except Exception as e:
                logger.error(f"❌ Failed to execute {signal} for {coin}: {e}")
                # 交易失败，不保存AI决策
        
        return summary
    
    async def execute_entry(
        self,
        coin: str,
        symbol: str,
        args: Dict,
        current_price: float
    ):
        """Execute entry order with real-time price validation."""
        leverage = args.get('leverage', 10)
        stop_loss = args.get('stop_loss')
        take_profit = args.get('profit_target')
        risk_usd = args.get('risk_usd')
        
        # 🆕 Get real-time price (AI may have taken 1-2 mins to decide)
        realtime_price = self.latest_prices.get(f"{coin}USDT")
        
        if realtime_price:
            # Determine trade direction first
            is_long = take_profit > current_price
            
            # Calculate slippage (signed: positive = price went up)
            price_change_pct = (realtime_price - current_price) / current_price * 100
            
            # 🛡️ 放宽滑点保护：只记录警告，不拒绝交易
            # - Long: price went UP (buying more expensive) = bad
            # - Short: price went DOWN (selling cheaper) = bad
            exec_protection = trading_config.risk_params.get('execution_protection', {})
            MAX_SLIPPAGE_WARNING = exec_protection.get('max_slippage_percent', 10.0)  # 提升到10%仅做警告
            LOG_THRESHOLD = exec_protection.get('log_slippage_threshold_percent', 0.1)
            
            unfavorable_slippage = (is_long and price_change_pct > 0) or (not is_long and price_change_pct < 0)
            
            # 只警告，不拒绝交易
            if unfavorable_slippage and abs(price_change_pct) > MAX_SLIPPAGE_WARNING:
                logger.warning(
                    f"⚠️ High unfavorable slippage: price {'rose' if price_change_pct > 0 else 'fell'} "
                    f"{abs(price_change_pct):.2f}% during AI decision "
                    f"({current_price:.4f} → {realtime_price:.4f}). "
                    f"{'Buying more expensive' if is_long else 'Selling cheaper'}. "
                    f"Proceeding with trade anyway (warning threshold: {MAX_SLIPPAGE_WARNING}%)"
                )
            
            # Log favorable slippage as good news!
            if not unfavorable_slippage and abs(price_change_pct) > LOG_THRESHOLD:
                logger.info(
                    f"✅ Favorable slippage: price {'fell' if is_long else 'rose'} "
                    f"{abs(price_change_pct):.2f}%! "
                    f"{'Buying cheaper' if is_long else 'Selling higher'}: {realtime_price:.4f}"
                )
            # Log unfavorable but acceptable slippage
            elif unfavorable_slippage and abs(price_change_pct) > LOG_THRESHOLD:
                logger.info(
                    f"💱 Acceptable slippage: {price_change_pct:+.2f}% "
                    f"({current_price:.4f} → {realtime_price:.4f})"
                )
            
            current_price = realtime_price
            
            # 🆕 Re-validate R/R ratio with new price (if enabled)
            if exec_protection.get('revalidate_rr_ratio', True):
                risk_distance = abs(current_price - stop_loss)
                reward_distance = abs(take_profit - current_price)
                
                if risk_distance > 0:
                    new_rr_ratio = reward_distance / risk_distance
                    min_rr = trading_config.risk_params['exit_strategy']['min_risk_reward_ratio']
                    
                    if new_rr_ratio < min_rr:
                        logger.warning(
                            f"⚠️ R/R ratio dropped to {new_rr_ratio:.2f} after price change "
                            f"(min: {min_rr}). Entry: {current_price:.4f}, "
                            f"SL: {stop_loss:.4f}, TP: {take_profit:.4f}. "
                            f"Skipping entry for {coin}"
                        )
                        return
        
        # Get account value for margin check
        account_value = self.portfolio.get_total_value()
        
        # Calculate position size with margin constraint (using real-time price)
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
    
    async def _monitor_shutdown_event(self):
        """Monitor shutdown event and set running flag (decoupled from signal handling)."""
        if self.shutdown_event:
            try:
                await self.shutdown_event.wait()
                logger.info("🛑 Shutdown event received, stopping bot...")
                self.running = False
                # 设置后立即返回，让主循环检测到
                return
            except asyncio.CancelledError:
                logger.info("🛑 Shutdown monitor cancelled")
                self.running = False
                return
    
    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down trading bot...")
        self.running = False
        
        # Stop WebSocket client
        if hasattr(self, 'ws_client'):
            try:
                await self.ws_client.stop()
            except Exception:
                pass
        
        # Close exchange connections
        try:
            if hasattr(self.data_client, 'exchange'):
                await self.data_client.exchange.close()
        except Exception:
            pass
        
        # Close exchange if it's different from data_client
        if self.exchange != self.data_client:
            try:
                if hasattr(self.exchange, 'close'):
                    await self.exchange.close()
            except Exception:
                pass
        
        logger.info("✅ Shutdown complete")

