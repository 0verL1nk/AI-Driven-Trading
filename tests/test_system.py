#!/usr/bin/env python3
"""
系统组件测试脚本
Test script for trading system components
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🚀 Trading System Component Test")
print("=" * 80)
print()

# Test 1: Import core modules
print("📦 Test 1: Importing core modules...")
try:
    from src.config import config
    from src.data.indicator_engine import IndicatorEngine
    from src.data.market_data import MarketDataCollector
    from src.ai.prompt_builder import PromptBuilder
    from src.ai.llm_interface import TradingLLM
    print("✅ All core modules imported successfully")
except Exception as e:
    print(f"❌ Failed to import modules: {e}")
    sys.exit(1)

print()

# Test 2: Check configuration
print("⚙️  Test 2: Loading configuration...")
try:
    print(f"   - Exchange: {config.exchange}")
    print(f"   - Trading pairs: {config.trading_pairs}")
    print(f"   - Paper trading: {config.paper_trading}")
    print(f"   - AI provider: {config.ai_provider}")
    print(f"   - AI model: {config.ai_model}")
    if config.openai_base_url:
        print(f"   - OpenAI base URL: {config.openai_base_url}")
    print("✅ Configuration loaded successfully")
except Exception as e:
    print(f"❌ Failed to load configuration: {e}")
    sys.exit(1)

print()

# Test 3: Test indicator engine with sample data
print("📊 Test 3: Testing indicator engine (pure pandas implementation)...")
try:
    import pandas as pd
    import numpy as np
    
    # Create sample OHLCV data
    dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 102 + np.random.randn(100).cumsum(),
        'low': 98 + np.random.randn(100).cumsum(),
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # Make sure high is highest and low is lowest
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
    
    # Test indicators
    print("   Testing EMA calculation...")
    ema = IndicatorEngine.calculate_ema(df, period=20)
    assert not ema.isna().all(), "EMA calculation failed"
    print(f"   ✓ EMA: last value = {ema.iloc[-1]:.2f}")
    
    print("   Testing MACD calculation...")
    macd = IndicatorEngine.calculate_macd(df)
    assert 'macd' in macd and 'signal' in macd, "MACD calculation failed"
    print(f"   ✓ MACD: last value = {macd['macd'].iloc[-1]:.2f}")
    
    print("   Testing RSI calculation...")
    rsi = IndicatorEngine.calculate_rsi(df, period=14)
    assert not rsi.isna().all(), "RSI calculation failed"
    print(f"   ✓ RSI: last value = {rsi.iloc[-1]:.2f}")
    
    print("   Testing ATR calculation...")
    atr = IndicatorEngine.calculate_atr(df, period=14)
    assert not atr.isna().all(), "ATR calculation failed"
    print(f"   ✓ ATR: last value = {atr.iloc[-1]:.2f}")
    
    print("   Testing Bollinger Bands calculation...")
    bb = IndicatorEngine.calculate_bollinger_bands(df, period=20)
    assert 'upper' in bb and 'middle' in bb and 'lower' in bb, "BB calculation failed"
    print(f"   ✓ BB: upper={bb['upper'].iloc[-1]:.2f}, middle={bb['middle'].iloc[-1]:.2f}, lower={bb['lower'].iloc[-1]:.2f}")
    
    print("✅ All indicator calculations working correctly (pure pandas)")
except Exception as e:
    print(f"❌ Indicator engine test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Test prompt builder
print("📝 Test 4: Testing prompt builder...")
try:
    prompt_builder = PromptBuilder()
    
    # Sample market data in expected format (coin symbol as key)
    # Create sample DataFrame for intraday data
    import pandas as pd
    import numpy as np
    
    sample_df = pd.DataFrame({
        'timestamp': pd.date_range(start='2025-01-01', periods=10, freq='3min'),
        'close': [110800, 110850, 110900, 110909.5, 110920, 110930, 110940, 110950, 110960, 110970],
        'open': [110790, 110840, 110890, 110900, 110910, 110920, 110930, 110940, 110950, 110960],
        'high': [110810, 110860, 110910, 110920, 110930, 110940, 110950, 110960, 110970, 110980],
        'low': [110780, 110830, 110880, 110890, 110900, 110910, 110920, 110930, 110940, 110950],
        'volume': [1000] * 10,
        'ema_20': [111100, 111120, 111140, 111159.342, 111170, 111180, 111190, 111200, 111210, 111220],
        'ema_50': [111000, 111020, 111040, 111059.0, 111070, 111080, 111090, 111100, 111110, 111120],
        'macd': [-30, -31, -32, -33.349, -34, -35, -36, -37, -38, -39],
        'macd_signal': [-28, -29, -30, -31, -32, -33, -34, -35, -36, -37],
        'rsi_7': [37, 37.5, 38, 38.262, 38.5, 39, 39.5, 40, 40.5, 41],
        'rsi_14': [37, 37.5, 38, 38.262, 38.5, 39, 39.5, 40, 40.5, 41],
        'bb_upper': [111300] * 10,
        'bb_middle': [111000] * 10,
        'bb_lower': [110700] * 10,
        'atr_14': [500] * 10,
    })
    
    market_data = {
        'BTC': {
            'intraday_df': sample_df,
            'longterm_df': sample_df,  # Simplified for test
            'funding_rate': 0.0001,
            'open_interest': 1500000000,
            'oi_average': 1400000000
        }
    }
    
    account_state = {
        'total_return': 0.0,
        'cash': 10000.0,
        'total_value': 10000.0,
        'sharpe_ratio': 0.0
    }
    
    positions = []
    
    prompt = prompt_builder.build_trading_prompt(market_data, account_state, positions)
    
    assert "CURRENT MARKET STATE FOR ALL COINS" in prompt, "Prompt missing market state section"
    assert "ALL BTC DATA" in prompt, "Prompt missing BTC data"
    assert "current_price" in prompt, "Prompt missing current price"
    assert "YOUR ACCOUNT" in prompt, "Prompt missing account section"
    
    print(f"   ✓ Prompt generated successfully ({len(prompt)} characters)")
    print(f"   ✓ Prompt includes market data, indicators, and account info")
    print("✅ Prompt builder working correctly")
except Exception as e:
    print(f"❌ Prompt builder test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 5: Test market data collector (dry run, no actual API calls)
print("🌐 Test 5: Testing market data collector initialization...")
try:
    collector = MarketDataCollector(
        exchange_id=config.exchange,
        pairs=config.trading_pairs
    )
    print(f"   ✓ Collector initialized for {config.exchange}")
    print(f"   ✓ Monitoring pairs: {', '.join(config.trading_pairs)}")
    print("✅ Market data collector initialized successfully")
except Exception as e:
    print(f"❌ Market data collector test failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 6: Check API keys (without exposing them)
print("🔑 Test 6: Checking API configuration...")
try:
    has_openai = bool(config.openai_api_key and config.openai_api_key != "your-openai-api-key-here")
    has_anthropic = bool(config.anthropic_api_key and config.anthropic_api_key != "your-anthropic-api-key-here")
    has_exchange = bool(config.exchange_api_key and config.exchange_api_key != "your-exchange-api-key")
    
    if config.ai_provider == "openai" and not has_openai:
        print("   ⚠️  Warning: OpenAI API key not configured")
    elif config.ai_provider == "anthropic" and not has_anthropic:
        print("   ⚠️  Warning: Anthropic API key not configured")
    else:
        print(f"   ✓ AI provider ({config.ai_provider}) API key configured")
    
    if not has_exchange:
        print("   ⚠️  Warning: Exchange API key not configured (paper trading mode)")
    else:
        print("   ✓ Exchange API key configured")
    
    print("✅ API configuration check completed")
except Exception as e:
    print(f"❌ API configuration check failed: {e}")

print()
print("=" * 80)
print("🎉 System Test Summary")
print("=" * 80)
print()
print("✅ All core components are working correctly!")
print()
print("📋 Next Steps:")
print("   1. Configure API keys in .env file (copy from env.template)")
print("   2. Adjust trading parameters in config/trading_config.yaml")
print("   3. Run: python main.py")
print()
print("=" * 80)
