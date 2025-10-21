"""Simple Pydantic-based output parser for trading decisions (no Langchain dependency)."""

import json
import logging
import re
from typing import Dict, Any

from .decision_models import TradingDecisions, CoinDecision, TradeSignalArgs

logger = logging.getLogger(__name__)


class OutputParserException(Exception):
    """Custom exception for parsing errors."""
    pass


class TradingDecisionParser:
    """
    Custom parser for trading decisions with enhanced error handling.
    
    Supports multiple JSON formats:
    1. Standard nested format with trade_signal_args
    2. Flat format (nof1.ai style)
    3. Mixed formats
    """
    
    def __init__(self):
        """Initialize parser."""
        pass
    
    def parse(self, text: str) -> Dict[str, Dict]:
        """
        Parse LLM output text to trading decisions dict.
        
        Args:
            text: Raw text from LLM
            
        Returns:
            Dict[str, Dict] - coin -> decision dict with trade_signal_args
            
        Raises:
            OutputParserException: If parsing fails
        """
        try:
            # Step 1: Clean the text
            cleaned_text = self._clean_text(text)
            
            # Step 2: Extract JSON
            json_text = self._extract_json(cleaned_text)
            
            # Step 3: Parse JSON
            raw_data = json.loads(json_text)
            
            # Step 4: Validate with Pydantic
            validated = self._validate_with_pydantic(raw_data)
            
            # Step 5: Convert to standard format
            result = validated.to_dict()
            
            logger.info(f"✅ Successfully parsed {len(result)} coin decisions")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Text (first 500 chars): {text[:500]}")
            raise OutputParserException(f"Invalid JSON: {e}")
            
        except Exception as e:
            logger.error(f"Parsing error: {e}")
            logger.error(f"Text (first 500 chars): {text[:500]}")
            raise OutputParserException(f"Failed to parse trading decisions: {e}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean text by removing reasoning tags and extra whitespace.
        
        Args:
            text: Raw text from LLM
            
        Returns:
            Cleaned text
        """
        # Remove <think></think> tags (for reasoning models)
        if "<think>" in text and "</think>" in text:
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
            logger.debug("Removed <think> tags")
        
        # Remove other common reasoning tags
        text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL)
        text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
        
        return text.strip()
    
    def _extract_json(self, text: str) -> str:
        """
        Extract JSON from text (handles markdown code blocks).
        
        Args:
            text: Cleaned text
            
        Returns:
            JSON string
        """
        # Try to extract from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        
        # Try to find JSON object boundaries
        # Look for outermost { }
        start_idx = text.find('{')
        if start_idx != -1:
            # Find matching closing brace
            brace_count = 0
            for i in range(start_idx, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[start_idx:i+1]
        
        # If no JSON found, return as-is and let json.loads fail
        return text.strip()
    
    def _validate_with_pydantic(self, raw_data: Dict[str, Any]) -> TradingDecisions:
        """
        Validate raw data with Pydantic models.
        Supports FLAT format (nof1.ai style) as primary format.
        
        Args:
            raw_data: Parsed JSON dict
            
        Returns:
            Validated TradingDecisions object
        """
        # Process data - support both flat and nested formats
        processed_data = {}
        
        for coin, decision_data in raw_data.items():
            # Skip non-coin keys
            if coin not in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']:
                logger.debug(f"Skipping non-coin key: {coin}")
                continue
            
            if not isinstance(decision_data, dict):
                logger.warning(f"Invalid decision data type for {coin}: {type(decision_data)}")
                continue
            
            # Check format
            if 'trade_signal_args' in decision_data:
                # Nested format - extract inner data
                logger.debug(f"{coin}: nested format detected")
                processed_data[coin] = decision_data['trade_signal_args']
            elif 'signal' in decision_data or 'coin' in decision_data:
                # Flat format (nof1.ai style) - use directly
                logger.debug(f"{coin}: flat format detected")
                processed_data[coin] = decision_data
            else:
                logger.warning(f"Unknown format for {coin}: missing 'signal' or 'trade_signal_args'")
        
        # Validate with Pydantic
        try:
            validated = TradingDecisions(**processed_data)
            logger.info(f"✅ Validated {len(processed_data)} coin decisions")
            return validated
        except Exception as e:
            logger.error(f"Pydantic validation error: {e}")
            logger.error(f"Data: {processed_data}")
            raise
    
    def get_format_instructions(self) -> str:
        """
        Get format instructions to include in prompt.
        
        Returns:
            Format instruction string (FLAT FORMAT)
        """
        # Use FLAT format (no trade_signal_args wrapper)
        instructions = f"""
OUTPUT FORMAT - FLAT JSON SCHEMA:

You MUST output a valid JSON object in FLAT format (NO nested trade_signal_args):

{{
  "BTC": {{
    "coin": "BTC",
    "signal": "entry" | "hold" | "close_position" | "no_action",
    "leverage": <integer 5-15>,
    "confidence": <float 0.5-1.0>,
    "risk_usd": <float>,
    "profit_target": <float>,  // Required for entry/hold
    "stop_loss": <float>,      // Required for entry/hold
    "invalidation_condition": "<string>",  // Required for entry/hold
    "quantity": <float>,       // For hold: current position size
    "justification": "<string>"  // Optional explanation
  }}
}}

TRADING-SPECIFIC RULES:
1. Use FLAT format - fields directly under coin name (NO trade_signal_args wrapper)
2. Signal types (IMPORTANT - choose based on current position status):
   - "entry": Open NEW position (use when NO current position)
   - "hold": Keep EXISTING position (use ONLY when position already exists)
   - "close_position": Close EXISTING position (use ONLY when position exists)
   - "no_action": Do nothing (use when NO position and not entering)
3. For "entry" signal: profit_target, stop_loss, invalidation_condition are REQUIRED
4. For "hold" signal: include quantity (current size) + existing targets
5. For "close_position": include justification explaining why
6. For "no_action": leverage/confidence can be any value (will auto-adjust to minimums)
7. Leverage: 5-15 for entry/hold (use higher only with high confidence)
8. Confidence: 0.5-1.0 for entry/hold, any value for no_action (auto-adjusted)
9. Risk per trade: maximum 2% of account value

⚠️ CRITICAL SIGNAL SELECTION RULES ⚠️:
- Check account positions FIRST before choosing signal!
- If "No current positions" → You can ONLY use "entry" OR "no_action"
- If you have positions → You can use "hold" OR "close_position"
- NEVER use "hold" when quantity is 0 or position doesn't exist
- NEVER use "entry" when you already have a position (use "hold" instead)

🎯 SIMPLIFICATION: You can OMIT coins where you want to take "no_action"!
- Only include coins you want to: enter, hold, or close
- If a coin is missing from your response, it will be treated as "no_action"
- This reduces response length and makes decisions clearer

Example 1 - Only entering ETH, all others no action (RECOMMENDED):
{{
  "ETH": {{
    "coin": "ETH",
    "signal": "entry",
    "leverage": 10,
    "confidence": 0.75,
    "risk_usd": 100.0,
    "profit_target": 3900.0,
    "stop_loss": 3700.0,
    "invalidation_condition": "If price closes below 3750"
  }}
}}
// BTC, SOL, BNB, XRP, DOGE omitted = no_action for all

Example 2 - Holding BTC, closing ETH, entering SOL:
{{
  "BTC": {{
    "coin": "BTC",
    "signal": "hold",
    "leverage": 10,
    "confidence": 0.75,
    "risk_usd": 200.0,
    "profit_target": 120000.0,
    "stop_loss": 100000.0,
    "invalidation_condition": "If price closes below 105000",
    "quantity": 0.12
  }},
  "ETH": {{
    "coin": "ETH",
    "signal": "close_position",
    "leverage": 10,
    "confidence": 0.9,
    "quantity": 2.5,
    "justification": "Target reached, taking profit"
  }},
  "SOL": {{
    "coin": "SOL",
    "signal": "entry",
    "leverage": 12,
    "confidence": 0.8,
    "risk_usd": 100.0,
    "profit_target": 195.0,
    "stop_loss": 175.0,
    "invalidation_condition": "If price closes below 175"
  }}
}}
// BNB, XRP, DOGE omitted = no_action

OUTPUT ONLY THE JSON OBJECT. NO MARKDOWN CODE BLOCKS. NO EXTRA TEXT.
"""
        return instructions


# Singleton instance
trading_parser = TradingDecisionParser()


def parse_trading_decision(text: str) -> Dict[str, Dict]:
    """
    Convenience function to parse trading decisions.
    
    Args:
        text: Raw LLM output text
        
    Returns:
        Dict[str, Dict] - coin -> decision dict
    """
    return trading_parser.parse(text)


if __name__ == "__main__":
    # Test parser
    test_nested = """
    {
      "BTC": {
        "trade_signal_args": {
          "coin": "BTC",
          "signal": "hold",
          "leverage": 10,
          "confidence": 0.75,
          "risk_usd": 200,
          "profit_target": 120000,
          "stop_loss": 100000,
          "invalidation_condition": "If price closes below 105000"
        }
      }
    }
    """
    
    test_flat = """
    {
      "ETH": {
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
    """
    
    test_with_markdown = """
    Here are my decisions:
    ```json
    {
      "SOL": {
        "trade_signal_args": {
          "coin": "SOL",
          "signal": "no_action",
          "leverage": 10,
          "confidence": 0.6,
          "risk_usd": 100
        }
      }
    }
    ```
    """
    
    parser = TradingDecisionParser()
    
    print("Testing nested format...")
    try:
        result = parser.parse(test_nested)
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\nTesting flat format...")
    try:
        result = parser.parse(test_flat)
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\nTesting markdown format...")
    try:
        result = parser.parse(test_with_markdown)
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")

