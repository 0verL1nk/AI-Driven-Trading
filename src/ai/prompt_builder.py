"""Prompt engineering for AI trading decisions - Exact nof1.ai format."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from .output_parser import trading_parser

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build structured prompts exactly matching nof1.ai format."""
    
    def __init__(self):
        self.call_count = 0
        self.start_time = datetime.now()
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt with output format requirements.
        
        Returns:
            System prompt string with format instructions
        """
        return """You are an expert cryptocurrency trading AI. Analyze market data and make trading decisions.

OUTPUT FORMAT REQUIREMENTS:
You MUST output ONLY valid JSON. No markdown code blocks, no explanatory text, just pure JSON.

Required format:
{
  "BTC": {
    "coin": "BTC",
    "signal": "entry" | "close_position" | "hold" | "no_action",
    "confidence": 0.0-1.0,
    "leverage": 5-15,
    "profit_target": number (required for entry/hold),
    "stop_loss": number (required for entry/hold),
    "risk_usd": number,
    "invalidation_condition": string,
    "justification": "optional explanation"
  },
  "ETH": { ... }
}

CRITICAL: Your ENTIRE response must be valid JSON only. Start with { and end with }. Do not include any text before or after the JSON."""
    
    def build_trading_prompt(
        self,
        market_data: Dict[str, Dict],
        account_state: Dict,
        positions: List[Dict]
    ) -> str:
        """
        Build complete trading prompt in exact nof1.ai format.
        
        Args:
            market_data: Dict with keys like 'BTC', 'ETH', etc., each containing:
                - intraday_df: DataFrame with 3-min OHLCV + indicators (last 10 rows)
                - longterm_df: DataFrame with 4-hour OHLCV + indicators (last 10 rows)
                - funding_rate: float
                - open_interest: float
                - oi_average: float
            account_state: Dict with 'total_return', 'cash', 'total_value', 'sharpe_ratio'
            positions: List of position dicts
        
        Returns:
            Formatted prompt string matching UserPrompt.md exactly
        """
        self.call_count += 1
        minutes_running = int((datetime.now() - self.start_time).total_seconds() / 60)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        
        prompt = f"""It has been {minutes_running} minutes since you started trading. The current time is {current_time} and you've been invoked {self.call_count} times. Below, we are providing you with a variety of state data, price data, and predictive signals so you can discover alpha. Below that is your current account information, value, performance, positions, etc.

ALL OF THE PRICE OR SIGNAL DATA BELOW IS ORDERED: OLDEST → NEWEST

Timeframes note: Unless stated otherwise in a section title, intraday series are provided at 3‑minute intervals. If a coin uses a different interval, it is explicitly stated in that coin's section.

CURRENT MARKET STATE FOR ALL COINS
"""
        
        # Build market data section for each coin
        for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']:
            if coin in market_data:
                prompt += self._format_coin_data(coin, market_data[coin])
        
        # Build account section
        prompt += self._format_account_section(account_state, positions)
        
        return prompt
    
    def _format_coin_data(self, coin: str, data: Dict) -> str:
        """Format market data for one coin exactly matching nof1.ai format."""
        intraday = data['intraday_df']
        longterm = data['longterm_df']
        
        # Get latest values
        latest = intraday.iloc[-1]
        last_10 = intraday.tail(10)
        
        section = f"ALL {coin} DATA\n"
        # current_price保持原始格式，不强制格式化
        section += f"current_price = {latest['close']}, "
        section += f"current_ema20 = {latest['ema_20']:.3f}, "
        section += f"current_macd = {latest['macd']:.3f}, "
        section += f"current_rsi (7 period) = {latest['rsi_7']:.3f}\n\n"
        
        # Perpetual contract data
        section += f"In addition, here is the latest {coin} open interest and funding rate for perps (the instrument you are trading):\n\n"
        section += f"Open Interest: Latest: {data['open_interest']:.2f} Average: {data['oi_average']:.2f}\n\n"
        section += f"Funding Rate: {data['funding_rate']:.6e}\n\n"
        
        # Intraday series - BTC默认是3分钟，其他币种需要明确说明
        if coin == 'BTC':
            section += "Intraday series (by minute, oldest → latest):\n\n"
            section += f"Mid prices: {self._format_list(last_10['close'])}\n\n"
        else:
            # ETH, SOL, BNB, XRP, DOGE 需要明确说明是3分钟间隔
            section += "Intraday series (3‑minute intervals, oldest → latest):\n\n"
            section += f"{coin} mid prices: {self._format_list(last_10['close'])}\n\n"
        
        section += f"EMA indicators (20‑period): {self._format_list(last_10['ema_20'])}\n\n"
        section += f"MACD indicators: {self._format_list(last_10['macd'])}\n\n"
        section += f"RSI indicators (7‑Period): {self._format_list(last_10['rsi_7'])}\n\n"
        section += f"RSI indicators (14‑Period): {self._format_list(last_10['rsi_14'])}\n\n"
        
        # Longer-term context (4-hour timeframe)
        lt_latest = longterm.iloc[-1]
        lt_last_10 = longterm.tail(10)
        
        section += "Longer‑term context (4‑hour timeframe):\n\n"
        section += f"20‑Period EMA: {lt_latest['ema_20']:.3f} vs. 50‑Period EMA: {lt_latest['ema_50']:.3f}\n\n"
        
        # Calculate ATR for 3-period and 14-period on 4H data
        atr_3 = longterm['atr_14'].tail(3).mean() if 'atr_14' in longterm.columns else 0
        atr_14 = lt_latest.get('atr_14', 0)
        section += f"3‑Period ATR: {atr_3:.3f} vs. 14‑Period ATR: {atr_14:.3f}\n\n"
        
        # Volume comparison
        avg_volume = longterm['volume'].mean()
        section += f"Current Volume: {lt_latest['volume']:.3f} vs. Average Volume: {avg_volume:.3f}\n\n"
        
        section += f"MACD indicators: {self._format_list(lt_last_10['macd'])}\n\n"
        section += f"RSI indicators (14‑Period): {self._format_list(lt_last_10['rsi_14'])}\n\n"
        
        return section
    
    def _format_list(self, series) -> str:
        """
        Format pandas Series as list string matching nof1.ai format.
        Preserves original precision from pandas Series.
        """
        values = series.tolist()
        # 直接转换为列表，保持原始精度（pandas会保持float/int类型）
        return str(values)
    
    def _format_account_section(self, account: Dict, positions: List[Dict]) -> str:
        """Format account information exactly matching nof1.ai format."""
        section = "HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE\n"
        section += f"Current Total Return (percent): {account.get('total_return', 0):.2f}%\n\n"
        section += f"Available Cash: {account.get('cash', 0):.2f}\n\n"
        section += f"Current Account Value: {account.get('total_value', 0):.2f}\n\n"
        
        # Format positions exactly as shown in UserPrompt.md
        if positions:
            section += "Current live positions & performance: "
            for pos in positions:
                # Output position dict as string representation
                section += f"{pos} "
            section += "\n\n"
        else:
            section += "No current positions.\n\n"
        
        section += f"Sharpe Ratio: {account.get('sharpe_ratio', 0):.3f}\n\n"
        
        return section

