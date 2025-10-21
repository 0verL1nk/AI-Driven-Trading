"""Validate and process LLM trading decisions."""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DecisionValidator:
    """Validate LLM trading decisions against risk parameters."""
    
    def __init__(self, risk_params: Dict):
        self.risk_params = risk_params
    
    def validate_decision(
        self,
        coin: str,
        decision: Dict,
        current_price: float,
        account_value: float
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a single coin's trading decision.
        
        Args:
            coin: Coin symbol (e.g., 'BTC')
            decision: Decision dict from LLM
            current_price: Current market price
            account_value: Total account value
        
        Returns:
            (is_valid, error_message) tuple
        """
        if 'trade_signal_args' not in decision:
            # No action decisions are valid
            return True, None
        
        args = decision['trade_signal_args']
        signal = args.get('signal')
        
        # Validate signal type
        if signal not in ['entry', 'hold', 'close_position', 'no_action']:
            return False, f"Invalid signal type: {signal}"
        
        # For hold and no_action, less validation needed
        if signal in ['hold', 'no_action']:
            return True, None
        
        # Validate entry/close_position signals
        if signal in ['entry', 'close_position']:
            # Check required fields
            required_fields = ['leverage', 'confidence', 'risk_usd']
            
            if signal == 'entry':
                required_fields.extend(['profit_target', 'stop_loss', 'invalidation_condition'])
            
            for field in required_fields:
                if field not in args:
                    return False, f"Missing required field: {field}"
            
            # Validate leverage
            leverage = args.get('leverage', 0)
            min_lev = self.risk_params['leverage']['min']
            max_lev = self.risk_params['leverage']['max']
            
            if not (min_lev <= leverage <= max_lev):
                return False, f"Leverage {leverage} outside allowed range [{min_lev}, {max_lev}]"
            
            # Validate confidence
            confidence = args.get('confidence', 0)
            if not (0.5 <= confidence <= 1.0):
                return False, f"Confidence {confidence} outside valid range [0.5, 1.0]"
            
            # Validate risk per trade
            risk_usd = args.get('risk_usd', 0)
            max_risk_percent = self.risk_params['position_sizing']['max_risk_per_trade_percent']
            max_risk = account_value * (max_risk_percent / 100)
            
            # Add small tolerance (0.1 USD) to avoid floating point precision issues
            # But still enforce that risk should be meaningfully less than max
            tolerance = 0.1
            if risk_usd > max_risk + tolerance:
                return False, f"Risk ${risk_usd:.2f} exceeds max ${max_risk:.2f} ({max_risk_percent}% of account)"
            
            # Validate stop loss and take profit for entry
            if signal == 'entry':
                stop_loss = args.get('stop_loss', 0)
                profit_target = args.get('profit_target', 0)
                
                if stop_loss <= 0 or profit_target <= 0:
                    return False, "Stop loss and profit target must be > 0"
                
                # Determine if long or short based on prices
                if profit_target > current_price:
                    # Long position
                    if stop_loss >= current_price:
                        return False, f"For long: stop loss {stop_loss} must be < current price {current_price}"
                    
                    # Check risk/reward ratio
                    risk_distance = current_price - stop_loss
                    reward_distance = profit_target - current_price
                    
                elif profit_target < current_price:
                    # Short position
                    if stop_loss <= current_price:
                        return False, f"For short: stop loss {stop_loss} must be > current price {current_price}"
                    
                    risk_distance = stop_loss - current_price
                    reward_distance = current_price - profit_target
                
                else:
                    return False, "Profit target cannot equal current price"
                
                # Check minimum risk/reward ratio
                if risk_distance > 0:
                    rr_ratio = reward_distance / risk_distance
                    min_rr = self.risk_params['exit_strategy']['min_risk_reward_ratio']
                    
                    if rr_ratio < min_rr:
                        # 提供详细的计算信息帮助调试
                        side = "LONG" if profit_target > current_price else "SHORT"
                        return False, (
                            f"Risk/reward ratio {rr_ratio:.2f} below minimum {min_rr}. "
                            f"Details ({side}): Entry={current_price:.2f}, "
                            f"SL={stop_loss:.2f}, TP={profit_target:.2f}, "
                            f"Risk=${risk_distance:.2f}, Reward=${reward_distance:.2f}. "
                            f"To fix: increase TP or tighten SL so that (TP-Entry) >= {min_rr}×(Entry-SL)"
                        )
        
        return True, None
    
    def validate_all_decisions(
        self,
        decisions: Dict[str, Dict],
        market_prices: Dict[str, float],
        account_value: float
    ) -> Dict[str, Dict]:
        """
        Validate all coin decisions and filter out invalid ones.
        
        Args:
            decisions: Dict of coin -> decision
            market_prices: Dict of coin -> current price
            account_value: Total account value
        
        Returns:
            Dict of validated decisions (invalid ones removed)
        """
        validated = {}
        
        for coin, decision in decisions.items():
            if coin not in market_prices:
                logger.warning(f"No market price for {coin}, skipping")
                continue
            
            is_valid, error = self.validate_decision(
                coin,
                decision,
                market_prices[coin],
                account_value
            )
            
            if is_valid:
                validated[coin] = decision
            else:
                logger.warning(f"Invalid decision for {coin}: {error}")
                # Log the decision for debugging
                logger.debug(f"Rejected decision: {decision}")
        
        return validated
    
    def calculate_position_size(
        self,
        risk_usd: float,
        entry_price: float,
        stop_loss: float,
        leverage: int,
        account_value: float = None
    ) -> float:
        """
        Calculate position size based on risk parameters.
        
        Args:
            risk_usd: Amount willing to risk in USD
            entry_price: Entry price
            stop_loss: Stop loss price
            leverage: Leverage multiplier
            account_value: Total account value (for margin check)
        
        Returns:
            Position size in base currency
        """
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            logger.error("Risk per unit is zero, cannot calculate position size")
            return 0
        
        # Check if stop loss is too tight (< 1% distance)
        sl_percent = (risk_per_unit / entry_price) * 100
        if sl_percent < 1.0:
            logger.warning(f"Stop loss very tight ({sl_percent:.2f}%), may result in large position size")
        
        # Position size based on risk
        base_position = risk_usd / risk_per_unit
        
        # Calculate required margin
        notional_value = base_position * entry_price
        required_margin = notional_value / leverage
        
        # If account_value provided, check margin constraint
        if account_value:
            # Maximum 30% of account value as margin for single trade
            max_margin = account_value * 0.30
            
            if required_margin > max_margin:
                logger.warning(
                    f"Required margin ${required_margin:.2f} exceeds max ${max_margin:.2f} "
                    f"(30% of account). Reducing position size."
                )
                # Reduce position size to fit margin constraint
                base_position = (max_margin * leverage) / entry_price
                
                # Recalculate actual risk
                actual_risk = base_position * risk_per_unit
                logger.warning(
                    f"Position size reduced. New risk: ${actual_risk:.2f} "
                    f"(target was ${risk_usd:.2f})"
                )
        
        return base_position

