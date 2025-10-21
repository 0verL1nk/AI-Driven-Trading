"""
WebSocket客户端 - 使用WebSocket获取实时市场数据
"""
import asyncio
import json
import logging
from typing import Dict, List, Callable
import websockets
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


class BinanceWebSocketClient:
    """Binance WebSocket客户端"""
    
    def __init__(self):
        self.ws_url = "wss://fstream.binance.com"
        self.connections = {}
        self.callbacks = {}
        self.running = False
        self.active_websockets = []  # 保存活跃的WebSocket连接
        self.tasks = []  # 保存运行中的任务
        
    async def subscribe_klines(self, symbols: List[str], interval: str = '3m', callback: Callable = None):
        """
        订阅K线数据
        
        Args:
            symbols: 交易对列表 ['btcusdt', 'ethusdt']
            interval: 时间间隔 1m, 3m, 5m, 15m, 1h, 4h
            callback: 回调函数，接收 (symbol, kline_data)
        """
        # 构建订阅参数
        streams = [f"{symbol.lower().replace('/', '').replace(':usdt', '')}@kline_{interval}" 
                   for symbol in symbols]
        
        ws_url = f"{self.ws_url}/stream?streams={'/'.join(streams)}"
        
        logger.info(f"Connecting to Binance WebSocket: {len(symbols)} symbols")
        
        websocket = None  # 初始化为None，避免UnboundLocalError
        try:
            async with websockets.connect(ws_url) as websocket:
                self.active_websockets.append(websocket)
                logger.info(f"✅ WebSocket connected for {len(symbols)} symbols")
                self.running = True
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        if 'data' in data:
                            stream_data = data['data']
                            if 'k' in stream_data:  # K线数据
                                kline = stream_data['k']
                                symbol = kline['s']
                                
                                # 解析K线数据
                                kline_info = {
                                    'timestamp': datetime.fromtimestamp(kline['t'] / 1000),
                                    'open': float(kline['o']),
                                    'high': float(kline['h']),
                                    'low': float(kline['l']),
                                    'close': float(kline['c']),
                                    'volume': float(kline['v']),
                                    'is_closed': kline['x']
                                }
                                
                                if callback:
                                    await callback(symbol, kline_info)
                                    
                    except asyncio.TimeoutError:
                        # 发送ping保持连接
                        if self.running:  # 只在运行时ping
                            await websocket.ping()
                            logger.debug("WebSocket ping sent")
                    except asyncio.CancelledError:
                        # 任务被取消，正常退出
                        logger.debug("K-line WebSocket task cancelled")
                        break
                        
        except asyncio.CancelledError:
            # 被取消时优雅退出
            logger.debug("K-line WebSocket connection cancelled")
        except Exception as e:
            if self.running:
                logger.error(f"WebSocket error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                # 递归重连
                await self.subscribe_klines(symbols, interval, callback)
            else:
                # 停止状态下的异常，静默处理
                logger.debug(f"WebSocket closed during shutdown: {e}")
        finally:
            # 清理（只有websocket存在时才清理）
            if websocket is not None and websocket in self.active_websockets:
                self.active_websockets.remove(websocket)
    
    async def subscribe_ticker(self, symbols: List[str], callback: Callable = None):
        """
        订阅ticker数据（实时价格）
        
        Args:
            symbols: 交易对列表
            callback: 回调函数，接收 (symbol, ticker_data)
        """
        streams = [f"{symbol.lower().replace('/', '').replace(':usdt', '')}@ticker" 
                   for symbol in symbols]
        
        ws_url = f"{self.ws_url}/stream?streams={'/'.join(streams)}"
        
        websocket = None  # 初始化为None，避免UnboundLocalError
        try:
            async with websockets.connect(ws_url) as websocket:
                self.active_websockets.append(websocket)
                logger.info(f"✅ Ticker WebSocket connected for {len(symbols)} symbols")
                
                while self.running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30)
                        data = json.loads(message)
                        
                        if 'data' in data:
                            ticker = data['data']
                            symbol = ticker['s']
                            
                            ticker_info = {
                                'symbol': symbol,
                                'price': float(ticker['c']),
                                'volume': float(ticker['v']),
                                'high': float(ticker['h']),
                                'low': float(ticker['l']),
                                'change_percent': float(ticker['P'])
                            }
                            
                            if callback:
                                await callback(symbol, ticker_info)
                                
                    except asyncio.TimeoutError:
                        if self.running:  # 只在运行时ping
                            await websocket.ping()
                    except asyncio.CancelledError:
                        # 任务被取消，正常退出
                        logger.debug("Ticker WebSocket task cancelled")
                        break
                        
        except asyncio.CancelledError:
            # 被取消时优雅退出
            logger.debug("Ticker WebSocket connection cancelled")
        except Exception as e:
            if self.running:
                logger.error(f"Ticker WebSocket error: {e}")
                await asyncio.sleep(5)
                await self.subscribe_ticker(symbols, callback)
            else:
                # 停止状态下的异常，静默处理
                logger.debug(f"Ticker WebSocket closed during shutdown: {e}")
        finally:
            # 清理（只有websocket存在时才清理）
            if websocket is not None and websocket in self.active_websockets:
                self.active_websockets.remove(websocket)
    
    async def get_historical_klines(self, symbol: str, interval: str = '3m', limit: int = 100) -> pd.DataFrame:
        """
        通过REST API获取历史K线数据（用于初始化）
        
        Args:
            symbol: 交易对，如 'BTCUSDT'
            interval: 时间间隔
            limit: 数量
            
        Returns:
            DataFrame with OHLCV data
        """
        import aiohttp
        
        # 清理symbol格式
        clean_symbol = symbol.upper().replace('/', '').replace(':USDT', '')
        
        url = f"https://fapi.binance.com/fapi/v1/klines"
        params = {
            'symbol': clean_symbol,
            'interval': interval,
            'limit': limit
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 转换为DataFrame
                        df = pd.DataFrame(data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        
                        # 只保留需要的列
                        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
                        
                        # 转换数据类型
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = df[col].astype(float)
                        
                        return df
                    else:
                        logger.error(f"Failed to fetch historical klines: {response.status}")
                        return pd.DataFrame()
                        
        except Exception as e:
            logger.error(f"Error fetching historical klines: {e}")
            return pd.DataFrame()
    
    async def stop(self):
        """停止所有WebSocket连接"""
        logger.info("Stopping WebSocket client...")
        self.running = False
        
        # 主动关闭所有WebSocket连接
        for ws in self.active_websockets:
            try:
                await ws.close()
            except Exception as e:
                logger.debug(f"Error closing websocket: {e}")
        
        self.active_websockets.clear()
        logger.info("WebSocket client stopped")

