"""Technical indicator calculation engine."""

import logging
from typing import Dict, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Try to import TA-Lib, fall back to pandas-ta, then to pandas if not available
HAS_TALIB = False
HAS_PANDAS_TA = False

try:
    import talib
    HAS_TALIB = True
    logger.info("Using TA-Lib for technical indicators")
except ImportError:
    try:
        import pandas_ta as ta
        HAS_PANDAS_TA = True
        logger.info("Using pandas-ta for technical indicators")
    except ImportError:
        logger.info("Using pandas for technical indicators (basic implementation)")


class IndicatorEngine:
    """Calculate technical indicators from OHLCV data."""
    
    @staticmethod
    def calculate_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Calculate Exponential Moving Average."""
        if HAS_TALIB:
            return talib.EMA(df['close'], timeperiod=period)
        elif HAS_PANDAS_TA:
            return df.ta.ema(length=period)
        else:
            # Pure pandas implementation
            return df['close'].ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate MACD indicator."""
        if HAS_TALIB:
            macd, signal, hist = talib.MACD(
                df['close'],
                fastperiod=12,
                slowperiod=26,
                signalperiod=9
            )
            return {'macd': macd, 'signal': signal, 'histogram': hist}
        elif HAS_PANDAS_TA:
            macd_indicator = ta.macd(df['close'])
            return {
                'macd': macd_indicator['MACD_12_26_9'],
                'signal': macd_indicator['MACDs_12_26_9'],
                'histogram': macd_indicator['MACDh_12_26_9']
            }
        else:
            # Pure pandas implementation
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            return {'macd': macd, 'signal': signal, 'histogram': histogram}
    
    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        if HAS_TALIB:
            return talib.RSI(df['close'], timeperiod=period)
        elif HAS_PANDAS_TA:
            return ta.rsi(df['close'], length=period)
        else:
            # Pure pandas implementation
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        if HAS_TALIB:
            return talib.ATR(df['high'], df['low'], df['close'], timeperiod=period)
        elif HAS_PANDAS_TA:
            return ta.atr(df['high'], df['low'], df['close'], length=period)
        else:
            # Pure pandas implementation
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            return true_range.rolling(period).mean()
    
    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands."""
        if HAS_TALIB:
            upper, middle, lower = talib.BBANDS(
                df['close'],
                timeperiod=period,
                nbdevup=2,
                nbdevdn=2
            )
            return {'upper': upper, 'middle': middle, 'lower': lower}
        elif HAS_PANDAS_TA:
            bb = ta.bbands(df['close'], length=period)
            return {
                'upper': bb[f'BBU_{period}_2.0'],
                'middle': bb[f'BBM_{period}_2.0'],
                'lower': bb[f'BBL_{period}_2.0']
            }
        else:
            # Pure pandas implementation
            middle = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = middle + (std * 2)
            lower = middle - (std * 2)
            return {'upper': upper, 'middle': middle, 'lower': lower}
    
    @classmethod
    def add_all_indicators(cls, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add all technical indicators to DataFrame.
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with added indicator columns
        """
        df = df.copy()
        
        # Trend indicators
        df['ema_20'] = cls.calculate_ema(df, 20)
        df['ema_50'] = cls.calculate_ema(df, 50)
        
        # MACD
        macd_data = cls.calculate_macd(df)
        df['macd'] = macd_data['macd']
        df['macd_signal'] = macd_data['signal']
        df['macd_histogram'] = macd_data['histogram']
        
        # RSI
        df['rsi_7'] = cls.calculate_rsi(df, 7)
        df['rsi_14'] = cls.calculate_rsi(df, 14)
        
        # ATR (volatility)
        df['atr_14'] = cls.calculate_atr(df, 14)
        
        # Bollinger Bands
        bb = cls.calculate_bollinger_bands(df)
        df['bb_upper'] = bb['upper']
        df['bb_middle'] = bb['middle']
        df['bb_lower'] = bb['lower']
        
        return df
    
    @staticmethod
    def format_for_prompt(df: pd.DataFrame, coin: str) -> str:
        """
        Format indicator data for AI prompt (matching nof1.ai format).
        
        Args:
            df: DataFrame with indicators
            coin: Coin symbol (e.g., 'BTC')
        
        Returns:
            Formatted string for prompt
        """
        latest = df.iloc[-1]
        last_n = df.tail(10)
        
        # Current state
        prompt = f"ALL {coin} DATA\n"
        prompt += f"current_price = {latest['close']:.2f}, "
        prompt += f"current_ema20 = {latest['ema_20']:.3f}, "
        prompt += f"current_macd = {latest['macd']:.3f}, "
        prompt += f"current_rsi (7 period) = {latest['rsi_7']:.3f}\n\n"
        
        # Intraday series (last 10 candles)
        prompt += "Intraday series (by minute, oldest → latest):\n\n"
        prompt += f"Mid prices: {list(last_n['close'].round(2))}\n\n"
        prompt += f"EMA indicators (20‑period): {list(last_n['ema_20'].round(3))}\n\n"
        prompt += f"MACD indicators: {list(last_n['macd'].round(3))}\n\n"
        prompt += f"RSI indicators (7‑Period): {list(last_n['rsi_7'].round(3))}\n\n"
        prompt += f"RSI indicators (14‑Period): {list(last_n['rsi_14'].round(3))}\n\n"
        
        return prompt

