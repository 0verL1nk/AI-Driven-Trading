"""Entry point for Web API Server (separate from trading bot)."""

import asyncio
import logging
import sys
import signal
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.web.api_server import WebAPIServer
from src.database import TradingDatabase
from src.config import settings


def setup_logging():
    """Configure logging for the web server."""
    log_format = '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Configure logging - only console output
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set library loggers to WARNING to reduce noise
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('fastapi').setLevel(logging.WARNING)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Web API Server for Trading Monitor')
    parser.add_argument(
        '--port',
        type=int,
        default=8541,
        help='Port number (default: 8541)'
    )
    parser.add_argument(
        '--db-type',
        choices=['sqlite', 'mysql'],
        default=None,
        help='Database type (default: from DB_TYPE env var or sqlite)'
    )
    parser.add_argument(
        '--db-path',
        default='trading_data.db',
        help='SQLite database path (default: trading_data.db)'
    )
    parser.add_argument(
        '--db-host',
        help='MySQL host (required for MySQL)'
    )
    parser.add_argument(
        '--db-port',
        type=int,
        default=3306,
        help='MySQL port (default: 3306)'
    )
    parser.add_argument(
        '--db-user',
        help='MySQL user (required for MySQL)'
    )
    parser.add_argument(
        '--db-password',
        help='MySQL password (required for MySQL)'
    )
    parser.add_argument(
        '--db-name',
        help='MySQL database name (required for MySQL)'
    )
    return parser.parse_args()


async def main():
    """Main entry point."""
    setup_logging()
    
    args = parse_args()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 80)
    logger.info("AI TRADING MONITOR - Web API Server")
    logger.info("=" * 80)
    
    # Prepare database configuration
    # Priority: command line args > environment variables (settings) > defaults
    db_type = args.db_type if args.db_type else settings.db_type
    
    db_kwargs = {}
    
    if db_type == 'sqlite':
        db_kwargs['db_path'] = args.db_path if args.db_path else 'trading_data.db'
    elif db_type == 'mysql':
        # Check if required parameters are provided (via args or settings)
        db_host = args.db_host if args.db_host else settings.db_host
        db_user = args.db_user if args.db_user else settings.db_user
        db_password = args.db_password if args.db_password else settings.db_password
        db_name = args.db_name if args.db_name else settings.db_name
        
        if not all([db_host, db_user, db_password, db_name]):
            logger.error("Missing required MySQL parameters!")
            logger.error("Provide via command line args (--db-host, --db-user, etc.) or environment variables (DB_HOST, DB_USER, etc.)")
            sys.exit(1)
        
        db_kwargs['host'] = db_host
        db_kwargs['port'] = args.db_port if args.db_port else (settings.db_port if settings.db_port else 3306)
        db_kwargs['user'] = db_user
        db_kwargs['password'] = db_password
        db_kwargs['database'] = db_name
        # SSL configuration
        db_kwargs['ssl_mode'] = settings.db_ssl_mode or 'REQUIRED'
        db_kwargs['ssl_ca'] = settings.db_ssl_ca
    
    logger.info(f"Database: {db_type.upper()}")
    if db_type == 'sqlite':
        logger.info(f"  Path: {db_kwargs.get('db_path', 'trading_data.db')}")
    else:
        logger.info(f"  Host: {db_kwargs.get('host', 'N/A')}:{db_kwargs.get('port', 'N/A')}")
        logger.info(f"  Database: {db_kwargs.get('database', 'N/A')}")
    logger.info(f"Web Server Port: {args.port}")
    logger.info("=" * 80 + "\n")
    
    # Initialize database
    db = TradingDatabase(db_type=db_type, **db_kwargs)
    logger.info(f"Database initialized ({db_type.upper()})")
    
    # Create Web API server
    # Note: running_callback is None since bot runs in separate process
    web_server = WebAPIServer(db=db, port=args.port, running_callback=None)
    
    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(signum, frame):
        """Handle interrupt signals (Ctrl+C)."""
        logger.info("\n⚠️  Received interrupt signal, initiating graceful shutdown...")
        shutdown_event.set()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start web server
        await web_server.start()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received, shutting down gracefully...")
        await web_server.stop()
    except asyncio.CancelledError:
        logger.info("⚠️  Server cancelled, shutting down gracefully...")
        await web_server.stop()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        await web_server.stop()
        sys.exit(1)
    finally:
        logger.info("👋 Web server stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete. Goodbye!")
        sys.exit(0)

