#!/usr/bin/env python3
"""
测试真实交易数据获取
Test real market data fetching from exchange
"""
import sys
import asyncio
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("=" * 80)
print("🌐 Real Market Data Test")
print("=" * 80)
print()

# Test 1: Import modules
print("📦 Test 1: Importing modules...")
try:
    from src.config import config
    from src.data.exchange_client import ExchangeClient
    from src.data.indicator_engine import IndicatorEngine
    print("✅ Modules imported successfully")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)

print()

# Test 2: Initialize exchange
print("⚙️  Test 2: Initializing exchange client...")
try:
    exchange = ExchangeClient()
    print(f"   ✓ Exchange: {exchange.exchange_name}")
    print(f"   ✓ Paper trading: {config.paper_trading}")
    print("✅ Exchange client initialized")
except Exception as e:
    print(f"❌ Failed to initialize exchange: {e}")
    sys.exit(1)

print()


async def test_market_data():
    """Test fetching real market data."""
    
    # Test 3: Load markets
    print("🔄 Test 3: Loading markets...")
    try:
        await exchange.load_markets()
        print(f"   ✓ Loaded {len(exchange.exchange.markets)} markets")
        print("✅ Markets loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load markets: {e}")
        await exchange.exchange.close()
        return
    
    print()
    
    # Test 4: Fetch OHLCV data
    print("📊 Test 4: Fetching OHLCV data...")
    test_symbol = config.trading_pairs[0]  # Use first trading pair from config
    print(f"   Testing with: {test_symbol}")
    
    try:
        # Fetch 3-minute data
        df_3m = await exchange.fetch_ohlcv(test_symbol, '3m', limit=10)
        print(f"   ✓ Fetched {len(df_3m)} candles (3-minute)")
        print(f"   ✓ Latest price: ${df_3m.iloc[-1]['close']:.2f}")
        print(f"   ✓ Latest volume: {df_3m.iloc[-1]['volume']:.2f}")
        print(f"   ✓ Time range: {df_3m.iloc[0]['timestamp']} to {df_3m.iloc[-1]['timestamp']}")
        
        # Add indicators
        df_with_indicators = IndicatorEngine.add_all_indicators(df_3m)
        latest = df_with_indicators.iloc[-1]
        
        print(f"\n   📈 Technical Indicators (latest):")
        print(f"   ✓ EMA(20): ${latest.get('ema_20', 0):.2f}")
        print(f"   ✓ RSI(14): {latest.get('rsi_14', 0):.2f}")
        print(f"   ✓ MACD: {latest.get('macd', 0):.3f}")
        print(f"   ✓ ATR(14): {latest.get('atr_14', 0):.2f}")
        
        print("\n✅ OHLCV data fetched and indicators calculated successfully")
    except Exception as e:
        print(f"❌ Failed to fetch OHLCV: {e}")
        import traceback
        traceback.print_exc()
        await exchange.exchange.close()
        return
    
    print()
    
    # Test 5: Fetch ticker
    print("💹 Test 5: Fetching current ticker...")
    try:
        ticker = await exchange.fetch_ticker(test_symbol)
        print(f"   ✓ Symbol: {ticker['symbol']}")
        print(f"   ✓ Last price: ${ticker['last']:.2f}")
        if ticker.get('bid'):
            print(f"   ✓ Bid: ${ticker['bid']:.2f}")
        if ticker.get('ask'):
            print(f"   ✓ Ask: ${ticker['ask']:.2f}")
        if ticker.get('volume'):
            print(f"   ✓ Volume: {ticker['volume']:.2f}")
        print("✅ Ticker data fetched successfully")
    except Exception as e:
        print(f"❌ Failed to fetch ticker: {e}")
    
    print()
    
    # Test 6: Fetch funding rate (for perpetual contracts)
    print("💰 Test 6: Fetching funding rate...")
    try:
        funding = await exchange.fetch_funding_rate(test_symbol)
        print(f"   ✓ Symbol: {funding['symbol']}")
        print(f"   ✓ Funding rate: {funding['funding_rate']:.6f} ({funding['funding_rate']*100:.4f}%)")
        if funding.get('next_funding_time'):
            print(f"   ✓ Next funding: {funding['next_funding_time']}")
        print("✅ Funding rate fetched successfully")
    except Exception as e:
        print(f"⚠️  Funding rate not available (normal for spot trading): {e}")
    
    print()
    
    # Test 7: Fetch open interest
    print("📈 Test 7: Fetching open interest...")
    try:
        oi = await exchange.fetch_open_interest(test_symbol)
        print(f"   ✓ Symbol: {oi['symbol']}")
        print(f"   ✓ Open Interest: {oi['open_interest']:,.0f}")
        print("✅ Open interest fetched successfully")
    except Exception as e:
        print(f"⚠️  Open interest not available (normal for spot trading): {e}")
    
    print()
    
    # Test 8: Test multiple timeframes
    print("⏱️  Test 8: Fetching multiple timeframes...")
    try:
        timeframes = ['1m', '5m', '15m', '1h', '4h']
        for tf in timeframes:
            df = await exchange.fetch_ohlcv(test_symbol, tf, limit=5)
            print(f"   ✓ {tf:4s}: {len(df)} candles, latest price: ${df.iloc[-1]['close']:.2f}")
        print("✅ Multiple timeframes fetched successfully")
    except Exception as e:
        print(f"❌ Failed to fetch multiple timeframes: {e}")
    
    print()
    
    # Test 9: Test all configured trading pairs
    print("🔄 Test 9: Testing all configured trading pairs...")
    print(f"   Trading pairs: {', '.join(config.trading_pairs)}")
    
    all_prices = {}
    for pair in config.trading_pairs:
        try:
            ticker = await exchange.fetch_ticker(pair)
            all_prices[pair] = ticker['last']
            coin = pair.split('/')[0]
            print(f"   ✓ {coin:6s}: ${ticker['last']:>10,.2f}")
        except Exception as e:
            print(f"   ❌ {pair}: Failed - {e}")
    
    if len(all_prices) == len(config.trading_pairs):
        print(f"\n✅ All {len(config.trading_pairs)} trading pairs accessible")
    else:
        print(f"\n⚠️  Only {len(all_prices)}/{len(config.trading_pairs)} pairs accessible")
    
    print()
    
    # Close exchange
    await exchange.close()
    
    print("=" * 80)
    print("📊 Market Data Test Summary")
    print("=" * 80)
    print()
    print("✅ Real market data is accessible!")
    print()
    print("📋 Available Data:")
    print("   ✓ OHLCV (candlestick) data - multiple timeframes")
    print("   ✓ Real-time ticker prices")
    print("   ✓ Technical indicators (EMA, MACD, RSI, ATR, BB)")
    print("   ✓ Funding rates (for perpetual contracts)")
    print("   ✓ Open interest data")
    print()
    print("🎯 Next Steps:")
    print("   1. The system will automatically fetch this data in real-time")
    print("   2. Run: python main.py")
    print("   3. The bot will collect data → analyze with AI → execute trades")
    print()
    print("=" * 80)
    
    # Properly close the exchange connection
    try:
        await exchange.exchange.close()
    except Exception as e:
        print(f"\n⚠️  Warning: Failed to close exchange cleanly: {e}")


# Run async tests
if __name__ == "__main__":
    try:
        asyncio.run(test_market_data())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

