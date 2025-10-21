"""Exchange client for real-time market data and trading."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import ccxt.async_support as ccxt
import pandas as pd

from ..config import settings, trading_config

logger = logging.getLogger(__name__)


class ExchangeClient:
    """Unified exchange client using CCXT."""
    
    def __init__(self):
        # Use 'binanceusdm' for USDT-margined futures instead of 'binance'
        if trading_config.exchange_name == 'binance':
            self.exchange_name = 'binanceusdm'  # CCXT's dedicated USDT-M futures class
            logger.info("Using CCXT 'binanceusdm' class for USDT-margined futures")
        else:
            self.exchange_name = trading_config.exchange_name
        
        self.exchange = self._initialize_exchange()
        self.markets_loaded = False
    
    def _initialize_exchange(self) -> ccxt.Exchange:
        """Initialize exchange connection."""
        exchange_class = getattr(ccxt, self.exchange_name)
        
        config = {
            'enableRateLimit': True,
            'timeout': 30000,  # 30秒超时（默认10秒可能不够）
        }
        
        # Add API keys only if they are configured
        has_api_key = settings.binance_api_key and settings.binance_api_key != ""
        has_api_secret = settings.binance_api_secret and settings.binance_api_secret != ""
        
        # Mode selection: Paper Trading vs Testnet vs Live Trading
        if settings.enable_paper_trading:
            # Mode 1: Local Paper Trading (no API calls for orders)
            logger.info("📊 Paper Trading Mode: Using mainnet for real market data")
            logger.info("   Orders will be simulated locally (not sent to exchange)")
            # Don't set API keys in paper trading mode - use public data only
        
        elif settings.use_testnet:
            # Mode 2: Binance Testnet (orders sent to testnet platform)
            if has_api_key and has_api_secret:
                config['apiKey'] = settings.binance_api_key
                config['secret'] = settings.binance_api_secret
                
                # 关键：为binanceusdm设置testnet的完整URL配置
                config['urls'] = {
                    'api': {
                        'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                        'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                        'fapiPrivateV2': 'https://testnet.binancefuture.com/fapi/v2',
                        'public': 'https://testnet.binancefuture.com/fapi/v1',
                        'private': 'https://testnet.binancefuture.com/fapi/v1',
                        # 禁用sapi调用（testnet不支持）
                        'sapi': 'https://testnet.binancefuture.com/fapi/v1',
                    }
                }
                config['options'] = {
                    'defaultType': 'future',
                    'fetchCurrencies': False,  # 禁用currency获取，避免调用sapi
                }
                
                logger.info("🧪 TESTNET Mode: Using Binance Futures Testnet")
                logger.info("   API URL: https://testnet.binancefuture.com/fapi/v1")
                logger.info("   ✅ Safe for testing - NO real money!")
                logger.info(f"   API Key (first 10 chars): {settings.binance_api_key[:10]}...")
                logger.info(f"   API Key (last 4 chars): ...{settings.binance_api_key[-4:]}")
            else:
                logger.error("⚠️ Testnet mode requires API keys!")
                logger.error("   Get testnet keys from: https://testnet.binancefuture.com")
                raise ValueError("Missing API keys for testnet mode")
        
        elif has_api_key and has_api_secret:
            # Mode 3: Live Trading (REAL MONEY!)
            config['apiKey'] = settings.binance_api_key
            config['secret'] = settings.binance_api_secret
            logger.info("🔴 LIVE Trading Mode: Using authenticated API")
            logger.warning("⚠️  REAL MONEY AT RISK - Orders will be executed on mainnet!")
        
        else:
            # Public data mode (read-only)
            logger.info("Using public API (read-only, no API keys)")
            logger.info("Fetching public market data from mainnet")
        
        return exchange_class(config)
    
    async def load_markets(self):
        """Load market information with retry."""
        if not self.markets_loaded:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.exchange.load_markets()
                    self.markets_loaded = True
                    logger.info(f"Loaded {len(self.exchange.markets)} markets from {self.exchange_name}")
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        logger.warning(f"Failed to load markets (attempt {attempt + 1}/{max_retries}): {e}")
                        logger.info(f"Retrying in {wait_time} seconds...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Failed to load markets after {max_retries} attempts")
                        raise
    
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '3m',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            timeframe: Candle timeframe (1m, 3m, 5m, 15m, 1h, 4h)
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    async def fetch_ticker(self, symbol: str) -> Dict:
        """Fetch current ticker price."""
        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'last': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'timestamp': ticker['timestamp']
            }
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
            raise
    
    async def fetch_funding_rate(self, symbol: str) -> Dict:
        """Fetch perpetual contract funding rate."""
        try:
            funding = await self.exchange.fetch_funding_rate(symbol)
            return {
                'symbol': symbol,
                'funding_rate': funding['fundingRate'],
                'funding_timestamp': funding['fundingTimestamp'],
                'next_funding_time': funding.get('fundingDatetime')
            }
        except Exception as e:
            logger.error(f"Error fetching funding rate for {symbol}: {e}")
            return {'symbol': symbol, 'funding_rate': 0.0}
    
    async def fetch_open_interest(self, symbol: str) -> Dict:
        """Fetch open interest data."""
        try:
            oi = await self.exchange.fetch_open_interest(symbol)
            # Handle different response formats
            if isinstance(oi, dict):
                oi_value = oi.get('openInterest') or oi.get('openInterestValue') or oi.get('info', {}).get('openInterest', 0)
            else:
                oi_value = float(oi) if oi else 0.0
            
            return {
                'symbol': symbol,
                'open_interest': float(oi_value),
                'timestamp': oi.get('timestamp') if isinstance(oi, dict) else None
            }
        except Exception as e:
            logger.error(f"Error fetching open interest for {symbol}: {e}")
            return {'symbol': symbol, 'open_interest': 0.0}
    
    async def fetch_balance(self) -> Dict:
        """Fetch account balance."""
        try:
            balance = await self.exchange.fetch_balance()
            return {
                'total': balance['total'],
                'free': balance['free'],
                'used': balance['used'],
                'USDT': balance['USDT'] if 'USDT' in balance else {}
            }
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            raise
    
    async def fetch_positions(self) -> List[Dict]:
        """Fetch current open positions."""
        try:
            positions = await self.exchange.fetch_positions()
            
            # Filter out zero positions
            active_positions = [
                pos for pos in positions
                if float(pos.get('contracts', 0)) > 0
            ]
            
            return active_positions
        
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            raise
    
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Create a market order.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            amount: Order size in base currency
            params: Additional order parameters (leverage, etc.)
        """
        try:
            order = await self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                params=params or {}
            )
            logger.info(f"Created {side} market order for {amount} {symbol}: {order['id']}")
            return order
        
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            raise
    
    async def create_stop_loss_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        stop_price: float
    ) -> Dict:
        """
        Create a stop-loss order (STOP_MARKET type).
        
        According to Binance U-margined futures API:
        - STOP_MARKET: only requires stopPrice (market order when triggered)
        - No price parameter needed
        """
        try:
            # Use STOP_MARKET type (market order triggered at stopPrice)
            params = {
                'stopPrice': stop_price,
            }
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='STOP_MARKET',  # Market stop-loss
                side=side,
                amount=amount,
                params=params
            )
            logger.info(f"Created STOP_MARKET at {stop_price} for {symbol}")
            return order
        
        except Exception as e:
            logger.error(f"Error creating stop-loss order: {e}")
            raise
    
    async def create_take_profit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        take_profit_price: float
    ) -> Dict:
        """
        Create a take-profit order (TAKE_PROFIT_MARKET type).
        
        According to Binance U-margined futures API:
        - TAKE_PROFIT_MARKET: only requires stopPrice (market order when triggered)
        - No price parameter needed
        """
        try:
            # Use TAKE_PROFIT_MARKET type (market order triggered at stopPrice)
            params = {
                'stopPrice': take_profit_price,
            }
            
            order = await self.exchange.create_order(
                symbol=symbol,
                type='TAKE_PROFIT_MARKET',  # Market take-profit
                side=side,
                amount=amount,
                params=params
            )
            logger.info(f"Created TAKE_PROFIT_MARKET at {take_profit_price} for {symbol}")
            return order
        
        except Exception as e:
            logger.error(f"Error creating take-profit order: {e}")
            raise
    
    async def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage for a symbol."""
        try:
            result = await self.exchange.set_leverage(leverage, symbol)
            logger.info(f"Set leverage to {leverage}x for {symbol}")
            return result
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
            raise
    
    async def close(self):
        """Close exchange connection."""
        await self.exchange.close()
        logger.info("Exchange connection closed")

