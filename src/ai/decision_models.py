"""Pydantic models for AI trading decisions - Ensures type safety and validation."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class SignalType(str, Enum):
    """Trading signal types."""
    ENTRY = "entry"
    HOLD = "hold"
    CLOSE_POSITION = "close_position"
    NO_ACTION = "no_action"


class TradeSignalArgs(BaseModel):
    """
    Trade signal arguments - core decision data.
    
    This matches the exact format used by nof1.ai.
    """
    coin: str = Field(..., description="Coin symbol (e.g., BTC, ETH)")
    signal: SignalType = Field(..., description="Trading signal type")
    
    # These fields are optional for no_action, will be auto-filled with defaults
    leverage: Optional[int] = Field(None, ge=1, le=15, description="Leverage multiplier (5-15x, optional for no_action)")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence level (0.0-1.0, optional for no_action)")
    risk_usd: Optional[float] = Field(None, ge=0, description="Risk amount in USD (optional for no_action)")
    
    # Entry/Hold specific fields
    profit_target: Optional[float] = Field(None, description="Take profit price")
    stop_loss: Optional[float] = Field(None, description="Stop loss price")
    invalidation_condition: Optional[str] = Field(None, description="Condition to invalidate position")
    
    # Optional fields
    quantity: Optional[float] = Field(None, description="Position quantity (for hold)")
    reasoning: Optional[str] = Field(None, description="Brief explanation of decision")
    justification: Optional[str] = Field(None, description="Justification for action")
    
    @field_validator('signal')
    @classmethod
    def validate_signal(cls, v):
        """Ensure signal is valid."""
        if isinstance(v, str):
            return SignalType(v.lower())
        return v
    
    @field_validator('leverage')
    @classmethod
    def validate_leverage(cls, v, info):
        """Validate leverage based on signal type."""
        signal = info.data.get('signal')
        
        # For no_action or close_position, use default if not provided
        if signal in [SignalType.NO_ACTION, SignalType.CLOSE_POSITION]:
            if v is None or v == 0:
                return 5  # Set default minimum
            return v
        
        # For entry/hold, leverage is required
        if v is None:
            raise ValueError(f"Leverage is required for {signal} signal")
        
        return v
    
    @field_validator('confidence')
    @classmethod
    def validate_confidence(cls, v, info):
        """Validate confidence based on signal type."""
        signal = info.data.get('signal')
        
        if signal in [SignalType.NO_ACTION, SignalType.CLOSE_POSITION]:
            # For no_action/close, use default if not provided
            if v is None:
                return 0.5  # Default confidence
            if v < 0.5:
                return 0.5
            return v
        else:
            # For entry/hold, confidence is required and must be >= 0.5
            if v is None:
                raise ValueError(f"Confidence is required for {signal} signal")
            if v < 0.5:
                raise ValueError(f"Confidence for {signal} must be >= 0.5, got {v}")
            return v
    
    @field_validator('risk_usd')
    @classmethod
    def validate_risk_usd(cls, v, info):
        """Validate risk_usd based on signal type."""
        signal = info.data.get('signal')
        
        if signal in [SignalType.NO_ACTION, SignalType.CLOSE_POSITION]:
            # For no_action/close, default to 0
            if v is None:
                return 0.0
            return v
        else:
            # For entry/hold, risk_usd is required
            if v is None:
                raise ValueError(f"risk_usd is required for {signal} signal")
            return v
    
    @field_validator('profit_target', 'stop_loss')
    @classmethod
    def validate_entry_fields(cls, v, info):
        """Validate that entry signals have required fields."""
        signal = info.data.get('signal')
        if signal == SignalType.ENTRY and v is None:
            raise ValueError(f"{info.field_name} is required for entry signals")
        return v
    
    class Config:
        use_enum_values = True  # Serialize enums as their values


class CoinDecision(TradeSignalArgs):
    """
    Decision for a single coin - FLAT FORMAT (nof1.ai style).
    
    Directly inherits all fields from TradeSignalArgs.
    No nesting required.
    
    Example (hold):
    {
      "coin": "ETH",
      "signal": "hold",
      "leverage": 15,
      "confidence": 0.68,
      "risk_usd": 600,
      "profit_target": 4010.71,
      "stop_loss": 3753.57,
      "invalidation_condition": "BTC breaks 106,000",
      "quantity": 5.83,
      "justification": ""
    }
    
    Example (entry):
    {
      "coin": "BTC",
      "signal": "entry",
      "leverage": 10,
      "confidence": 0.75,
      "risk_usd": 200,
      "profit_target": 110000,
      "stop_loss": 105000,
      "invalidation_condition": "Price closes below 105000"
    }
    """
    # Add justification field (nof1.ai uses this instead of reasoning)
    justification: Optional[str] = Field(None, description="Justification for the decision")
    
    def get_trade_args(self) -> TradeSignalArgs:
        """Get TradeSignalArgs (for backward compatibility)."""
        return TradeSignalArgs(
            coin=self.coin,
            signal=self.signal,
            leverage=self.leverage,
            confidence=self.confidence,
            risk_usd=self.risk_usd,
            profit_target=self.profit_target,
            stop_loss=self.stop_loss,
            invalidation_condition=self.invalidation_condition,
            quantity=self.quantity,
            reasoning=self.reasoning or self.justification
        )


class TradingDecisions(BaseModel):
    """
    Complete trading decisions for all coins - FLAT FORMAT (nof1.ai style).
    
    Example:
    {
        "BTC": {
            "coin": "BTC",
            "signal": "hold",
            "leverage": 10,
            "confidence": 0.75,
            "risk_usd": 200,
            ...
        },
        "ETH": {...}
    }
    """
    BTC: Optional[CoinDecision] = None
    ETH: Optional[CoinDecision] = None
    SOL: Optional[CoinDecision] = None
    BNB: Optional[CoinDecision] = None
    XRP: Optional[CoinDecision] = None
    DOGE: Optional[CoinDecision] = None
    
    def to_dict(self) -> dict:
        """
        Convert to dict format (flat or nested based on need).
        
        Returns:
            Dict[str, Dict] - coin -> decision dict with trade_signal_args wrapper
        """
        result = {}
        for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']:
            decision = getattr(self, coin, None)
            if decision:
                # Return with trade_signal_args wrapper for backward compatibility
                result[coin] = {
                    'trade_signal_args': decision.model_dump(exclude_none=True)
                }
        return result
    
    class Config:
        extra = 'allow'  # Allow additional coins


# Example usage and validation
if __name__ == "__main__":
    # Test flat format (nof1.ai style)
    flat_decision = {
        "BTC": {
            "coin": "BTC",
            "signal": "hold",
            "leverage": 10,
            "confidence": 0.75,
            "risk_usd": 200,
            "profit_target": 120000,
            "stop_loss": 100000,
            "invalidation_condition": "If price closes below 105000",
            "quantity": 0.1
        }
    }
    
    # Test nested format (our format)
    nested_decision = {
        "ETH": {
            "trade_signal_args": {
                "coin": "ETH",
                "signal": "entry",
                "leverage": 15,
                "confidence": 0.8,
                "risk_usd": 300,
                "profit_target": 4500,
                "stop_loss": 3500,
                "invalidation_condition": "If price closes below 3600"
            }
        }
    }
    
    # Validate both formats
    try:
        decisions = TradingDecisions(**flat_decision)
        print("✅ Flat format validated")
        print(decisions.to_dict())
    except Exception as e:
        print(f"❌ Flat format error: {e}")
    
    try:
        decisions = TradingDecisions(**nested_decision)
        print("✅ Nested format validated")
        print(decisions.to_dict())
    except Exception as e:
        print(f"❌ Nested format error: {e}")

