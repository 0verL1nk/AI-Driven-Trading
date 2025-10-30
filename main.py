"""Entry point for the AI trading bot."""

import asyncio
import logging
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.trading_bot import TradingBot


def setup_logging():
    """Configure logging for the application."""
    log_format = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler('logs/trading.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set library loggers to WARNING to reduce noise
    logging.getLogger('ccxt').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)


async def main():
    """Main entry point."""
    setup_logging()
    
    logger = logging.getLogger(__name__)
    logger.info("="  * 80)
    logger.info("AI-DRIVEN CRYPTOCURRENCY TRADING SYSTEM")
    logger.info("Based on nof1.ai architecture")
    logger.info("=" * 80)
    
    # Import config for display
    from src.config import settings, trading_config
    
    # Prepare database configuration from environment variables
    db_type = settings.db_type
    
    db_kwargs = {}
    
    if db_type == 'sqlite':
        db_kwargs['db_path'] = 'trading_data.db'
    elif db_type == 'mysql':
        # Check if required parameters are provided via environment variables
        if not all([settings.db_host, settings.db_user, settings.db_password, settings.db_name]):
            logger.error("Missing required MySQL parameters!")
            logger.error("Please set environment variables: DB_HOST, DB_USER, DB_PASSWORD, DB_NAME")
            sys.exit(1)
        
        db_kwargs['host'] = settings.db_host
        db_kwargs['port'] = settings.db_port if settings.db_port else 3306
        db_kwargs['user'] = settings.db_user
        db_kwargs['password'] = settings.db_password
        db_kwargs['database'] = settings.db_name
        # SSL configuration
        db_kwargs['ssl_mode'] = settings.db_ssl_mode or 'REQUIRED'
        db_kwargs['ssl_ca'] = settings.db_ssl_ca
    
    # Display configuration
    logger.info("\n" + "=" * 80)
    logger.info("SYSTEM CONFIGURATION")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Paper Trading: {'ENABLED ✅' if settings.enable_paper_trading else 'DISABLED ⚠️ (LIVE TRADING)'}")
    logger.info("")
    logger.info("AI Configuration:")
    logger.info(f"  Provider: {trading_config.ai_provider}")
    logger.info(f"  Model: {trading_config.ai_model}")
    
    # 显示base_url配置来源
    base_url = settings.openai_base_url or trading_config.ai_base_url
    if base_url:
        source = "Environment Variable" if settings.openai_base_url else "Config File"
        logger.info(f"  Base URL: {base_url}")
        logger.info(f"  Source: {source} (Third-party/Custom API)")
    else:
        logger.info(f"  Base URL: Official OpenAI API (https://api.openai.com/v1)")
    
    logger.info(f"  Temperature: {trading_config.trading_config['ai']['temperature']}")
    logger.info(f"  Max Tokens: {trading_config.trading_config['ai']['max_tokens']}")
    logger.info(f"  Decision Interval: {trading_config.decision_interval_minutes} minutes")
    logger.info("")
    logger.info("Trading Configuration:")
    logger.info(f"  Trading Pairs: {len(trading_config.trading_pairs)} pairs")
    for pair in trading_config.trading_pairs:
        logger.info(f"    - {pair}")
    logger.info("")
    logger.info("Risk Management:")
    logger.info(f"  Max Risk per Trade: {trading_config.max_risk_per_trade}%")
    logger.info(f"  Leverage Range: {trading_config.leverage_config['min']}-{trading_config.leverage_config['max']}x")
    logger.info(f"  Max Daily Drawdown: {trading_config.max_daily_drawdown}%")
    logger.info("")
    if settings.enable_paper_trading:
        initial_balance = trading_config.trading_config['paper_trading']['initial_balance']
        logger.info(f"Paper Trading Settings:")
        logger.info(f"  Initial Balance: ${initial_balance:,.2f} USDT")
    logger.info("")
    logger.info("Database Configuration:")
    logger.info(f"  Type: {db_type.upper()}")
    if db_type == 'sqlite':
        logger.info(f"  Path: {db_kwargs.get('db_path', 'trading_data.db')}")
    else:
        logger.info(f"  Host: {db_kwargs.get('host', 'N/A')}:{db_kwargs.get('port', 'N/A')}")
        logger.info(f"  Database: {db_kwargs.get('database', 'N/A')}")
    logger.info("")
    logger.info("=" * 80 + "\n")
    
    # Create and start trading bot
    bot = TradingBot(db_type=db_type, **db_kwargs)
    
    # Set up signal handlers for graceful shutdown (decoupled)
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        """Handle interrupt signals (Ctrl+C)."""
        logger.info("\n⚠️  Received interrupt signal (Ctrl+C), initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start bot with shutdown event
        await bot.start(shutdown_event=shutdown_event)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received, shutting down gracefully...")
        await bot.shutdown()
    except asyncio.CancelledError:
        logger.info("⚠️  Tasks cancelled, shutting down gracefully...")
        await bot.shutdown()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        await bot.shutdown()
        sys.exit(1)
    finally:
        logger.info("👋 Trading bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete. Goodbye!")
        sys.exit(0)

