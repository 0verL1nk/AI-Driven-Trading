"""
Market Data Collector
收集市场数据：实时行情、K线数据、订单簿等
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from src.data.exchange_client import ExchangeClient
from src.data.indicator_engine import IndicatorEngine

logger = logging.getLogger(__name__)


class MarketDataCollector:
    """市场数据收集器"""
    
    def __init__(self, exchange_id: str, pairs: List[str]):
        """
        初始化市场数据收集器
        
        Args:
            exchange_id: 交易所ID（如 'binance'）- 暂未使用，从配置读取
            pairs: 交易对列表（如 ['BTC/USDT:USDT', 'ETH/USDT:USDT']）
        """
        self.exchange_client = ExchangeClient()
        self.pairs = pairs
        self.cache = {}  # 数据缓存
        logger.info(f"Market data collector initialized for {self.exchange_client.exchange_name} with pairs: {pairs}")
    
    async def get_current_prices(self) -> Dict[str, float]:
        """
        获取当前价格
        
        Returns:
            {symbol: price} 字典
        """
        prices = {}
        for pair in self.pairs:
            try:
                ticker = await self.exchange_client.fetch_ticker(pair)
                prices[pair] = ticker['last']
            except Exception as e:
                logger.error(f"Failed to fetch price for {pair}: {e}")
                prices[pair] = None
        return prices
    
    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1m',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期（'1m', '5m', '1h'等）
            limit: 数据条数
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        try:
            ohlcv = await self.exchange_client.fetch_ohlcv(symbol, timeframe, limit)
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol}: {e}")
            return pd.DataFrame()
    
    async def get_market_data_with_indicators(
        self,
        symbol: str,
        timeframe: str = '3m',
        limit: int = 200
    ) -> Dict:
        """
        获取带技术指标的市场数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            limit: 数据条数
            
        Returns:
            包含价格、指标等的字典
        """
        try:
            # 获取K线数据
            df = await self.get_ohlcv(symbol, timeframe, limit)
            
            if df.empty:
                return {}
            
            # 计算技术指标
            df = IndicatorEngine.add_all_indicators(df)
            
            # 提取最新数据
            latest = df.iloc[-1]
            
            result = {
                'symbol': symbol,
                'current_price': float(latest['close']),
                'ema20': float(latest.get('ema_20', 0)),
                'macd': float(latest.get('macd', 0)),
                'macd_signal': float(latest.get('macd_signal', 0)),
                'rsi': float(latest.get('rsi_14', 0)),
                'atr': float(latest.get('atr_14', 0)),
                'bb_upper': float(latest.get('bb_upper', 0)),
                'bb_middle': float(latest.get('bb_middle', 0)),
                'bb_lower': float(latest.get('bb_lower', 0)),
                'volume': float(latest['volume']),
                # 历史数据（最近N条）
                'price_history': df['close'].tail(50).tolist(),
                'ema_history': df.get('ema_20', pd.Series()).tail(50).tolist(),
                'macd_history': df.get('macd', pd.Series()).tail(50).tolist(),
                'rsi_history': df.get('rsi_14', pd.Series()).tail(50).tolist(),
                'volume_history': df['volume'].tail(50).tolist(),
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get market data with indicators for {symbol}: {e}")
            return {}
    
    async def get_all_market_data(self) -> Dict[str, Dict]:
        """
        获取所有交易对的市场数据
        
        Returns:
            {symbol: market_data} 字典
        """
        all_data = {}
        
        for pair in self.pairs:
            data = await self.get_market_data_with_indicators(pair)
            if data:
                all_data[pair] = data
        
        return all_data
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """
        获取订单簿
        
        Args:
            symbol: 交易对
            limit: 深度
            
        Returns:
            订单簿数据
        """
        try:
            orderbook = await self.exchange_client.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'timestamp': orderbook.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Failed to fetch order book for {symbol}: {e}")
            return {'bids': [], 'asks': [], 'timestamp': None}
    
    async def get_account_balance(self) -> Dict:
        """
        获取账户余额
        
        Returns:
            账户余额信息
        """
        try:
            balance = await self.exchange_client.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            return {}
    
    def close(self):
        """关闭连接"""
        if self.exchange_client:
            self.exchange_client.close()

