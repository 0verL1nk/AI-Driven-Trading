"""Test script to verify system components."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_imports():
    """Test if all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.config import settings, trading_config
        print("✓ Config module")
        
        from src.data.exchange_client import ExchangeClient
        print("✓ Exchange client")
        
        from src.data.indicator_engine import IndicatorEngine
        print("✓ Indicator engine")
        
        from src.ai.prompt_builder import PromptBuilder
        print("✓ Prompt builder")
        
        from src.ai.llm_interface import TradingLLM
        print("✓ LLM interface")
        
        from src.ai.decision_validator import DecisionValidator
        print("✓ Decision validator")
        
        from src.execution.order_manager import OrderManager
        print("✓ Order manager")
        
        from src.execution.portfolio_manager import PortfolioManager
        print("✓ Portfolio manager")
        
        from src.execution.paper_trading import PaperTradingEngine
        print("✓ Paper trading engine")
        
        from src.trading_bot import TradingBot
        print("✓ Trading bot")
        
        print("\n✅ All imports successful!")
        return True
    
    except Exception as e:
        print(f"\n❌ Import error: {e}")
        return False


async def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    try:
        from src.config import settings, trading_config
        
        print(f"  Trading pairs: {len(trading_config.trading_pairs)}")
        print(f"  AI provider: {trading_config.ai_provider}")
        print(f"  AI model: {trading_config.ai_model}")
        print(f"  Decision interval: {trading_config.decision_interval_minutes} min")
        print(f"  Max risk per trade: {trading_config.max_risk_per_trade}%")
        print(f"  Paper trading: {settings.enable_paper_trading}")
        
        print("\n✅ Configuration loaded successfully!")
        return True
    
    except Exception as e:
        print(f"\n❌ Config error: {e}")
        return False


async def test_paper_trading():
    """Test paper trading engine."""
    print("\nTesting paper trading engine...")
    
    try:
        from src.execution.paper_trading import PaperTradingEngine
        
        engine = PaperTradingEngine(initial_balance=10000.0)
        
        # Test balance fetch
        balance = await engine.fetch_balance()
        print(f"  Initial balance: ${balance['USDT']['total']:.2f}")
        
        # Test positions fetch
        positions = await engine.fetch_positions()
        print(f"  Positions: {len(positions)}")
        
        # Test market order
        order = await engine.create_market_order(
            symbol="BTC/USDT:USDT",
            side="buy",
            amount=0.01
        )
        print(f"  Test order created: {order['id']}")
        
        print("\n✅ Paper trading engine working!")
        return True
    
    except Exception as e:
        print(f"\n❌ Paper trading error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_indicator_engine():
    """Test indicator calculation."""
    print("\nTesting indicator engine...")
    
    try:
        import pandas as pd
        from src.data.indicator_engine import IndicatorEngine
        
        # Create sample OHLCV data
        data = {
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='3min'),
            'open': [100 + i * 0.1 for i in range(100)],
            'high': [101 + i * 0.1 for i in range(100)],
            'low': [99 + i * 0.1 for i in range(100)],
            'close': [100.5 + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        }
        df = pd.DataFrame(data)
        
        # Add indicators
        engine = IndicatorEngine()
        df_with_indicators = engine.add_all_indicators(df)
        
        print(f"  Original columns: {len(df.columns)}")
        print(f"  With indicators: {len(df_with_indicators.columns)}")
        print(f"  Indicators added: {list(df_with_indicators.columns[5:])}")
        
        # Test formatting for prompt
        prompt_text = engine.format_for_prompt(df_with_indicators, 'BTC')
        print(f"  Prompt text length: {len(prompt_text)} chars")
        
        print("\n✅ Indicator engine working!")
        return True
    
    except Exception as e:
        print(f"\n❌ Indicator engine error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_prompt_builder():
    """Test prompt building."""
    print("\nTesting prompt builder...")
    
    try:
        import pandas as pd
        from src.ai.prompt_builder import PromptBuilder
        from src.data.indicator_engine import IndicatorEngine
        
        # Create sample data
        engine = IndicatorEngine()
        builder = PromptBuilder()
        
        # Sample OHLCV
        data = {
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='3min'),
            'open': [100 + i * 0.1 for i in range(100)],
            'high': [101 + i * 0.1 for i in range(100)],
            'low': [99 + i * 0.1 for i in range(100)],
            'close': [100.5 + i * 0.1 for i in range(100)],
            'volume': [1000 + i * 10 for i in range(100)]
        }
        df = pd.DataFrame(data)
        df = engine.add_all_indicators(df)
        
        # Build market data
        market_data = {
            'BTC': {
                'intraday_df': df,
                'longterm_df': df,
                'funding_rate': -0.0001,
                'open_interest': 27000.0,
                'oi_average': 26500.0
            }
        }
        
        account_state = {
            'total_return': 5.5,
            'cash': 9500.0,
            'total_value': 10550.0,
            'sharpe_ratio': 0.8
        }
        
        positions = []
        
        # Build prompt
        prompt = builder.build_trading_prompt(market_data, account_state, positions)
        
        print(f"  Prompt length: {len(prompt)} chars")
        print(f"  Contains 'ALL BTC DATA': {'ALL BTC DATA' in prompt}")
        print(f"  Contains 'ACCOUNT INFORMATION': {'ACCOUNT INFORMATION' in prompt}")
        
        # Show first 500 chars
        print(f"\n  First 500 chars:\n{prompt[:500]}...")
        
        print("\n✅ Prompt builder working!")
        return True
    
    except Exception as e:
        print(f"\n❌ Prompt builder error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("AI TRADING SYSTEM - Component Tests")
    print("=" * 60)
    
    results = []
    
    results.append(await test_imports())
    results.append(await test_config())
    results.append(await test_indicator_engine())
    results.append(await test_prompt_builder())
    results.append(await test_paper_trading())
    
    print("\n" + "=" * 60)
    print(f"Test Results: {sum(results)}/{len(results)} passed")
    print("=" * 60)
    
    if all(results):
        print("\n🎉 All tests passed! System is ready to run.")
        print("\nNext steps:")
        print("1. Configure .env file with API keys")
        print("2. Review config/trading_config.yaml")
        print("3. Run: python main.py")
    else:
        print("\n⚠️  Some tests failed. Please fix errors before running.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

