"""Main trading bot orchestrator."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List

from .config import settings, trading_config
from .data.exchange_client import ExchangeClient
from .data.indicator_engine import IndicatorEngine
from .ai.prompt_builder import PromptBuilder
from .ai.llm_interface import TradingLLM
from .ai.decision_validator import DecisionValidator
from .execution.order_manager import OrderManager
from .execution.portfolio_manager import PortfolioManager
from .execution.paper_trading import PaperTradingEngine

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
        if settings.enable_paper_trading:
            logger.info("Running in PAPER TRADING mode")
            paper_balance = trading_config.trading_config['paper_trading']['initial_balance']
            self.exchange = PaperTradingEngine(initial_balance=paper_balance)
        else:
            logger.info("Running in LIVE TRADING mode")
            self.exchange = ExchangeClient()
        
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
        initial_balance = trading_config.trading_config['paper_trading']['initial_balance']
        self.portfolio = PortfolioManager(initial_balance=initial_balance)
        
        self.running = False
        self.decision_interval = trading_config.decision_interval_minutes * 60  # Convert to seconds
    
    async def start(self):
        """Start the trading bot."""
        logger.info("=" * 60)
        logger.info("AI TRADING BOT STARTING")
        logger.info("=" * 60)
        
        # Load markets
        if not settings.enable_paper_trading:
            await self.exchange.load_markets()
        
        self.running = True
        
        try:
            await self.run_trading_loop()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
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
                positions = await self.exchange.fetch_positions()
                
                account_state = self.portfolio.calculate_account_state(balance, positions)
                formatted_positions = self.portfolio.format_positions_for_prompt(positions)
                
                logger.info(f"Account Value: ${account_state['total_value']:.2f}")
                logger.info(f"Return: {account_state['total_return']:.2f}%")
                logger.info(f"Positions: {account_state['num_positions']}")
                
                # Step 3: Check invalidation conditions
                logger.info("Step 3: Checking invalidation conditions...")
                current_prices = {
                    coin: data['intraday_df'].iloc[-1]['close']
                    for coin, data in market_data.items()
                }
                
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
                decisions = await self.llm.decide(
                    prompt,
                    temperature=trading_config.trading_config['ai']['temperature'],
                    max_tokens=trading_config.trading_config['ai']['max_tokens']
                )
                
                logger.info(f"Received decisions for {len(decisions)} coins")
                
                # Step 6: Validate decisions
                logger.info("Step 6: Validating decisions...")
                validated_decisions = self.validator.validate_all_decisions(
                    decisions,
                    current_prices,
                    account_state['total_value']
                )
                
                logger.info(f"Validated {len(validated_decisions)}/{len(decisions)} decisions")
                
                # Step 7: Execute trades
                logger.info("Step 7: Executing trades...")
                await self.execute_decisions(validated_decisions, formatted_positions, current_prices)
                
                # Step 8: Log performance
                performance = self.portfolio.get_performance_metrics()
                if performance:
                    logger.info(f"\nPerformance Summary:")
                    logger.info(f"  Total Trades: {performance['total_trades']}")
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
                # Fetch 3-minute intraday data
                intraday_df = await self.exchange.fetch_ohlcv(
                    symbol=pair,
                    timeframe='3m',
                    limit=100
                )
                
                # Add indicators
                intraday_df = self.indicator_engine.add_all_indicators(intraday_df)
                
                # Fetch 4-hour longer-term data
                longterm_df = await self.exchange.fetch_ohlcv(
                    symbol=pair,
                    timeframe='4h',
                    limit=100
                )
                
                # Add indicators to long-term data
                longterm_df = self.indicator_engine.add_all_indicators(longterm_df)
                
                # Fetch funding rate and open interest
                funding_data = await self.exchange.fetch_funding_rate(pair)
                oi_data = await self.exchange.fetch_open_interest(pair)
                
                # Calculate OI average (last 24 hours approximation)
                oi_average = oi_data.get('open_interest', 0) * 0.98  # Placeholder
                
                market_data[coin] = {
                    'intraday_df': intraday_df,
                    'longterm_df': longterm_df,
                    'funding_rate': funding_data.get('funding_rate', 0),
                    'open_interest': oi_data.get('open_interest', 0),
                    'oi_average': oi_average
                }
                
                logger.debug(f"Collected data for {coin}")
            
            except Exception as e:
                logger.error(f"Failed to collect data for {coin}: {e}")
        
        return market_data
    
    async def execute_decisions(
        self,
        decisions: Dict[str, Dict],
        current_positions: List[Dict],
        current_prices: Dict[str, float]
    ):
        """Execute validated trading decisions."""
        position_map = {pos['symbol']: pos for pos in current_positions}
        
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
                
                elif signal == 'close_position':
                    # Close existing position
                    if coin in position_map:
                        await self.order_manager.execute_close(
                            coin,
                            symbol,
                            position_map[coin]
                        )
                        logger.info(f"Closed position for {coin}")
                
                elif signal == 'hold':
                    logger.debug(f"Holding position for {coin}")
                
            except Exception as e:
                logger.error(f"Failed to execute {signal} for {coin}: {e}")
    
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
        
        # Calculate position size
        position_size = self.validator.calculate_position_size(
            risk_usd=risk_usd,
            entry_price=current_price,
            stop_loss=stop_loss,
            leverage=leverage
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
        
        await self.exchange.close()
        logger.info("Shutdown complete")

