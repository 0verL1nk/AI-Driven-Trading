"""Test Langchain + Pydantic output parser."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai.output_parser import trading_parser, parse_trading_decision
from ai.decision_models import TradingDecisions


def test_nested_format():
    """Test nof1.ai nested format with trade_signal_args."""
    print("\n" + "=" * 60)
    print("Test 1: Nested Format (Our Standard)")
    print("=" * 60)
    
    nested_json = """
    {
      "BTC": {
        "trade_signal_args": {
          "coin": "BTC",
          "signal": "hold",
          "leverage": 10,
          "confidence": 0.75,
          "risk_usd": 200.0,
          "profit_target": 120000.0,
          "stop_loss": 100000.0,
          "invalidation_condition": "If price closes below 105000 on 3-min candle"
        }
      },
      "ETH": {
        "trade_signal_args": {
          "coin": "ETH",
          "signal": "entry",
          "leverage": 15,
          "confidence": 0.85,
          "risk_usd": 300.0,
          "profit_target": 4500.0,
          "stop_loss": 3700.0,
          "invalidation_condition": "If price closes below 3750"
        }
      }
    }
    """
    
    try:
        result = parse_trading_decision(nested_json)
        print(f"✅ SUCCESS: Parsed {len(result)} coins")
        for coin, decision in result.items():
            args = decision.get('trade_signal_args', {})
            print(f"  {coin}: {args.get('signal')} @ leverage {args.get('leverage')}x")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_flat_format():
    """Test flat format (backward compatibility)."""
    print("\n" + "=" * 60)
    print("Test 2: Flat Format (Legacy)")
    print("=" * 60)
    
    flat_json = """
    {
      "SOL": {
        "coin": "SOL",
        "signal": "no_action",
        "leverage": 10,
        "confidence": 0.6,
        "risk_usd": 100.0
      }
    }
    """
    
    try:
        result = parse_trading_decision(flat_json)
        print(f"✅ SUCCESS: Parsed {len(result)} coins")
        for coin, decision in result.items():
            args = decision.get('trade_signal_args', {})
            print(f"  {coin}: {args.get('signal')} @ leverage {args.get('leverage')}x")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_markdown_wrapped():
    """Test JSON wrapped in markdown code blocks."""
    print("\n" + "=" * 60)
    print("Test 3: Markdown Wrapped JSON")
    print("=" * 60)
    
    markdown_json = """
    Here are my trading decisions:
    
    ```json
    {
      "BNB": {
        "trade_signal_args": {
          "coin": "BNB",
          "signal": "close_position",
          "leverage": 10,
          "confidence": 0.7,
          "risk_usd": 150.0,
          "reasoning": "Invalidation condition triggered"
        }
      }
    }
    ```
    
    That's my analysis.
    """
    
    try:
        result = parse_trading_decision(markdown_json)
        print(f"✅ SUCCESS: Parsed {len(result)} coins")
        for coin, decision in result.items():
            args = decision.get('trade_signal_args', {})
            print(f"  {coin}: {args.get('signal')}")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_real_nof1_format():
    """Test real nof1.ai format from conversation.json."""
    print("\n" + "=" * 60)
    print("Test 4: Real nof1.ai Format")
    print("=" * 60)
    
    real_json = """
    {
        "DOGE": {
            "invalidation_condition": "If the price closes below 0.180 on a 3-minute candle",
            "quantity": 27858,
            "stop_loss": 0.175355,
            "signal": "hold",
            "profit_target": 0.212275,
            "coin": "DOGE",
            "leverage": 10,
            "risk_usd": 257.13,
            "confidence": 0.65,
            "justification": ""
        },
        "BTC": {
            "invalidation_condition": "If the price closes below 105000 on a 3-minute candle",
            "quantity": 0.12,
            "stop_loss": 102026.675,
            "signal": "hold",
            "profit_target": 118136.15,
            "coin": "BTC",
            "leverage": 10,
            "risk_usd": 619.2345,
            "confidence": 0.75,
            "justification": ""
        }
    }
    """
    
    try:
        result = parse_trading_decision(real_json)
        print(f"✅ SUCCESS: Parsed {len(result)} coins")
        for coin, decision in result.items():
            args = decision.get('trade_signal_args', {})
            print(f"  {coin}: {args.get('signal')} @ {args.get('confidence')} confidence")
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def test_validation_errors():
    """Test Pydantic validation catches errors."""
    print("\n" + "=" * 60)
    print("Test 5: Validation Errors")
    print("=" * 60)
    
    # Invalid leverage (out of range)
    invalid_json = """
    {
      "XRP": {
        "trade_signal_args": {
          "coin": "XRP",
          "signal": "entry",
          "leverage": 50,
          "confidence": 0.8,
          "risk_usd": 200.0,
          "profit_target": 3.0,
          "stop_loss": 2.0,
          "invalidation_condition": "If price closes below 2.2"
        }
      }
    }
    """
    
    try:
        result = parse_trading_decision(invalid_json)
        print(f"⚠️ WARNING: Should have failed but didn't")
        return False
    except Exception as e:
        print(f"✅ SUCCESS: Correctly caught validation error")
        print(f"   Error: {str(e)[:100]}...")
        return True


def test_format_instructions():
    """Test format instructions generation."""
    print("\n" + "=" * 60)
    print("Test 6: Format Instructions")
    print("=" * 60)
    
    instructions = trading_parser.get_format_instructions()
    
    if len(instructions) > 100:
        print(f"✅ SUCCESS: Generated {len(instructions)} chars of instructions")
        print("\nFirst 300 chars:")
        print(instructions[:300] + "...")
        return True
    else:
        print(f"❌ FAILED: Instructions too short")
        return False


if __name__ == "__main__":
    print("\n" + "🧪" * 30)
    print("LANGCHAIN + PYDANTIC PARSER TEST SUITE")
    print("🧪" * 30)
    
    results = []
    
    results.append(("Nested Format", test_nested_format()))
    results.append(("Flat Format", test_flat_format()))
    results.append(("Markdown Wrapped", test_markdown_wrapped()))
    results.append(("Real nof1.ai Format", test_real_nof1_format()))
    results.append(("Validation Errors", test_validation_errors()))
    results.append(("Format Instructions", test_format_instructions()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        sys.exit(1)

