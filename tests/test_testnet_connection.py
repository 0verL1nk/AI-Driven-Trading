#!/usr/bin/env python3
"""测试Testnet API连接"""

import asyncio
import ccxt.async_support as ccxt
from src.config import settings

async def test_testnet():
    """测试Testnet API连接"""
    
    print("=" * 60)
    print("🧪 测试币安Testnet API连接")
    print("=" * 60)
    
    # 显示配置
    print(f"\n📋 当前配置:")
    print(f"   ENABLE_PAPER_TRADING: {settings.enable_paper_trading}")
    print(f"   USE_TESTNET: {settings.use_testnet}")
    print(f"   API Key (前10字符): {settings.binance_api_key[:10]}...")
    print(f"   API Key (后4字符): ...{settings.binance_api_key[-4:]}")
    
    # 创建exchange实例
    print(f"\n🔗 创建Testnet连接...")
    
    exchange = ccxt.binanceusdm({
        'apiKey': settings.binance_api_key,
        'secret': settings.binance_api_secret,
        'enableRateLimit': True,
        'urls': {
            'api': {
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivateV2': 'https://testnet.binancefuture.com/fapi/v2',
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
                'sapi': 'https://testnet.binancefuture.com/fapi/v1',
            }
        },
        'options': {
            'defaultType': 'future',
            'fetchCurrencies': False,  # 禁用currency获取
        }
    })
    
    try:
        # 测试1: 获取市场信息
        print(f"\n✅ 测试1: 加载市场信息...")
        await exchange.load_markets()
        print(f"   成功加载 {len(exchange.markets)} 个交易对")
        
        # 测试2: 获取账户余额
        print(f"\n✅ 测试2: 获取账户余额...")
        balance = await exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {})
        print(f"   USDT余额: {usdt_balance.get('free', 0):.2f}")
        print(f"   总余额: {usdt_balance.get('total', 0):.2f}")
        
        # 测试3: 获取持仓
        print(f"\n✅ 测试3: 获取持仓...")
        positions = await exchange.fetch_positions()
        active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
        print(f"   活跃持仓数: {len(active_positions)}")
        
        # 显示API端点信息
        print(f"\n📡 API端点信息:")
        print(f"   URLs: {exchange.urls}")
        
        print(f"\n" + "=" * 60)
        print(f"🎉 所有测试通过！Testnet连接正常！")
        print(f"=" * 60)
        
        return True
        
    except ccxt.AuthenticationError as e:
        print(f"\n❌ 认证错误: {e}")
        print(f"\n💡 可能的原因:")
        print(f"   1. API Key/Secret不正确")
        print(f"   2. API Key不是从 testnet.binancefuture.com 获取")
        print(f"   3. API Key已过期或被删除")
        print(f"\n🔧 解决方法:")
        print(f"   1. 访问 https://testnet.binancefuture.com")
        print(f"   2. 登录后进入 API Management")
        print(f"   3. 创建新的API Key")
        print(f"   4. 更新 .env 文件中的密钥")
        return False
        
    except Exception as e:
        print(f"\n❌ 连接错误: {e}")
        return False
        
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(test_testnet())

