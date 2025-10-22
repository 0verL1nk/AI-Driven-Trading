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
        section += f"current_price = {latest['close']}, "
        section += f"current_ema20 = {latest['ema_20']:.3f}, "
        section += f"current_macd = {latest['macd']:.3f}, "
        section += f"current_rsi (7 period) = {latest['rsi_7']:.3f}\n\n"
        
        # Perpetual contract data
        section += f"In addition, here is the latest {coin} open interest and funding rate for perps (the instrument you are trading):\n\n"
        section += f"Open Interest: Latest: {data['open_interest']:.2f} Average: {data['oi_average']:.2f}\n\n"
        section += f"Funding Rate: {data['funding_rate']:.6e}\n\n"
        
        # Intraday series
        section += "Intraday series (by minute, oldest → latest):\n\n"
        
        # Format mid prices as list
        if coin in ['SOL', 'BNB', 'DOGE', 'XRP']:
            section += f"{coin} mid prices: {self._format_list(last_10['close'])}\n\n"
        else:
            section += f"Mid prices: {self._format_list(last_10['close'])}\n\n"
        
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
        """Format pandas Series as list string matching nof1.ai format."""
        values = series.tolist()
        # Round to appropriate decimal places
        rounded = [round(v, 3) for v in values]
        return str(rounded)
    
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
        
        # Add explicit trading philosophy guidance
        section += "=" * 80 + "\n"
        section += "TRADING PHILOSOPHY & STRATEGY GUIDANCE (MUST READ)\n"
        section += "=" * 80 + "\n"
        section += "⏰ IMPORTANT: Due to AI decision-making latency (data processing, analysis, validation),\n"
        section += "   you are NOT suited for scalping or high-frequency trading.\n\n"
        
        section += "🎯 RECOMMENDED STRATEGY: SWING TRADING\n"
        section += "   - Focus on larger price movements over hours to days\n"
        section += "   - Target significant market moves (3%+ potential profit)\n"
        section += "   - Avoid quick in-and-out trades that depend on precise timing\n"
        section += "   - Quality over quantity - fewer, better-planned trades\n\n"
        
        section += "⏱️ MINIMUM HOLDING TIME GUIDANCE:\n"
        section += "   - Consider positions you can hold for at least 2-4 hours\n"
        section += "   - Ideal targets: 12-48 hours for most trades\n"
        section += "   - Only enter if you see a clear multi-hour/day trend potential\n\n"
        
        section += "📈 FOCUS AREAS FOR ENTRY SIGNALS:\n"
        section += "   - Clear trend continuations or reversals\n"
        section += "   - Support/resistance breakouts with volume confirmation\n"
        section += "   - Major technical pattern completions\n"
        section += "   - Significant fundamental catalysts or market sentiment shifts\n\n"
        
        section += "🚫 AVOID:\n"
        section += "   - Minute-by-minute price fluctuations\n"
        section += "   - Scalping opportunities requiring split-second timing\n"
        section += "   - Over-trading (multiple trades per hour)\n"
        section += "   - Chasing small 0.5-1% moves\n\n"
        
        section += "💡 PATIENCE IS PROFITABLE: Wait for high-conviction setups with clear risk/reward\n"
        section += "=" * 80 + "\n\n"
        
        # Add explicit risk management constraints
        from ..config import trading_config
        total_value = account.get('total_value', 10000)
        max_risk_percent = trading_config.risk_params['position_sizing']['max_risk_per_trade_percent']
        max_risk_usd = total_value * (max_risk_percent / 100)
        min_leverage = trading_config.risk_params['leverage']['min']
        max_leverage = trading_config.risk_params['leverage']['max']
        min_rr_ratio = trading_config.risk_params['exit_strategy']['min_risk_reward_ratio']
        
        section += "=" * 80 + "\n"
        section += "RISK MANAGEMENT RULES (MUST FOLLOW)\n"
        section += "=" * 80 + "\n"
        section += f"1. Maximum risk per trade: {max_risk_percent}% of account = ${max_risk_usd:.2f} USD\n"
        section += f"   ⚠️ IMPORTANT: Your 'risk_usd' must be LESS THAN ${max_risk_usd:.2f} (not equal to it)\n\n"
        
        section += f"2. Leverage range: {min_leverage}x to {max_leverage}x (choose based on confidence)\n"
        section += f"   - High confidence (0.75-1.0): use 12-15x\n"
        section += f"   - Medium confidence (0.65-0.74): use 8-11x\n"
        section += f"   - Low confidence (0.50-0.64): use 5-7x\n\n"
        
        section += f"3. Minimum risk/reward ratio: {min_rr_ratio}:1 ⚠️ THIS IS CRITICAL!\n"
        section += f"   How to calculate (MUST follow this formula):\n"
        section += f"   \n"
        section += f"   For LONG positions:\n"
        section += f"     - Risk per unit = entry_price - stop_loss\n"
        section += f"     - Reward per unit = profit_target - entry_price\n"
        section += f"     - Risk/Reward Ratio = Reward / Risk\n"
        section += f"   \n"
        section += f"   For SHORT positions:\n"
        section += f"     - Risk per unit = stop_loss - entry_price\n"
        section += f"     - Reward per unit = entry_price - profit_target\n"
        section += f"     - Risk/Reward Ratio = Reward / Risk\n"
        section += f"   \n"
        section += f"   ✅ EXAMPLE (LONG BTC at $100,000):\n"
        section += f"     - Entry: $100,000\n"
        section += f"     - Stop Loss: $98,000 (2% below entry)\n"
        section += f"     - Profit Target: $103,000 (3% above entry)\n"
        section += f"     - Risk = $100,000 - $98,000 = $2,000\n"
        section += f"     - Reward = $103,000 - $100,000 = $3,000\n"
        section += f"     - R/R Ratio = $3,000 / $2,000 = 1.5 ✅ VALID\n"
        section += f"   \n"
        section += f"   ❌ BAD EXAMPLE (R/R too low):\n"
        section += f"     - Entry: $100,000\n"
        section += f"     - Stop Loss: $98,000 (risk = $2,000)\n"
        section += f"     - Profit Target: $101,000 (reward = $1,000)\n"
        section += f"     - R/R Ratio = $1,000 / $2,000 = 0.5 ❌ REJECTED!\n"
        section += f"   \n"
        section += f"   💡 TIP: To meet {min_rr_ratio}:1 ratio:\n"
        section += f"     profit_target distance >= {min_rr_ratio} × stop_loss distance\n\n"
        
        section += f"4. Every 'entry' signal MUST have:\n"
        section += f"   - stop_loss: Price level (must be < entry for long, > entry for short)\n"
        section += f"     ⚠️ IMPORTANT: Stop loss must be at least 2% away from entry price!\n"
        section += f"     (Too tight stop loss = very large position size = margin insufficient error)\n"
        section += f"   - profit_target: Price level (ensure R/R >= {min_rr_ratio}:1)\n"
        section += f"   - invalidation_condition: Clear condition like 'If price closes below X on 3-min candle'\n"
        section += f"   - All prices must be realistic and based on current market price\n\n"
        
        section += f"5. For 'no_action' or 'hold' signals, you can set:\n"
        section += f"   - risk_usd = 0\n"
        section += f"   - leverage = {min_leverage} (minimum allowed)\n"
        section += f"   - confidence >= 0.5\n"
        section += f"   - stop_loss and profit_target can be 0 or null\n"
        section += "=" * 80 + "\n\n"
        
        # Add Langchain auto-generated format instructions
        section += "OUTPUT FORMAT INSTRUCTIONS\n"
        section += "=" * 80 + "\n"
        section += trading_parser.get_format_instructions()
        section += "\n" + "=" * 80 + "\n"
        
        return section

