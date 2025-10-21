#!/usr/bin/env python3
"""详细诊断API连接问题"""

import asyncio
import ccxt.async_support as ccxt
from src.config import settings
import json

async def diagnose():
    """详细诊断"""
    
    print("=" * 70)
    print("🔍 详细API诊断")
    print("=" * 70)
    
    # 1. 显示配置
    print(f"\n📋 环境变量配置:")
    print(f"   ENABLE_PAPER_TRADING: {settings.enable_paper_trading}")
    print(f"   USE_TESTNET: {settings.use_testnet}")
    print(f"   API Key完整: {settings.binance_api_key}")
    print(f"   Secret完整: {settings.binance_api_secret}")
    
    # 2. 创建exchange
    print(f"\n🔧 创建exchange实例...")
    exchange = ccxt.binanceusdm({
        'apiKey': settings.binance_api_key,
        'secret': settings.binance_api_secret,
        'enableRateLimit': True,
        'verbose': True,  # 启用详细日志
        'urls': {
            'api': {
                'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                'fapiPrivateV2': 'https://testnet.binancefuture.com/fapi/v2',
                'public': 'https://testnet.binancefuture.com/fapi/v1',
                'private': 'https://testnet.binancefuture.com/fapi/v1',
            }
        },
        'options': {
            'defaultType': 'future'
        }
    })
    
    # 3. 显示实际URLs
    print(f"\n📡 Exchange URLs配置:")
    print(json.dumps(exchange.urls, indent=2))
    
    # 4. 测试公共接口（不需要API Key）
    print(f"\n✅ 测试1: 公共接口（不需要API Key）")
    try:
        ticker = await exchange.fetch_ticker('BTC/USDT:USDT')
        print(f"   成功！BTC价格: ${ticker['last']}")
    except Exception as e:
        print(f"   失败: {e}")
    
    # 5. 测试私有接口（需要API Key）
    print(f"\n🔐 测试2: 私有接口（需要API Key）")
    print(f"   尝试获取账户余额...")
    try:
        balance = await exchange.fetch_balance()
        print(f"   ✅ 成功！")
        print(f"   USDT余额: {balance.get('USDT', {}).get('free', 0)}")
    except ccxt.AuthenticationError as e:
        print(f"   ❌ 认证失败: {e}")
        print(f"\n🔍 问题分析:")
        print(f"   1. API Key是否真的来自 testnet.binancefuture.com?")
        print(f"   2. 登录 https://testnet.binancefuture.com 验证API Key是否存在")
        print(f"   3. 检查API Key权限（需要勾选 'Enable Reading' 和 'Enable Futures'）")
    except Exception as e:
        print(f"   ❌ 其他错误: {e}")
    
    # 6. 手动测试API endpoint
    print(f"\n🌐 测试3: 手动测试testnet endpoint")
    print(f"   尝试访问: https://testnet.binancefuture.com/fapi/v1/time")
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get('https://testnet.binancefuture.com/fapi/v1/time') as resp:
                data = await resp.json()
                print(f"   ✅ Testnet可访问！服务器时间: {data}")
    except Exception as e:
        print(f"   ❌ 无法访问testnet: {e}")
    
    await exchange.close()
    
    print(f"\n" + "=" * 70)
    print(f"💡 建议:")
    print(f"=" * 70)
    print(f"1. 访问 https://testnet.binancefuture.com")
    print(f"2. 登录你的账号")
    print(f"3. 进入 API Management")
    print(f"4. 检查你的API Key是否存在且未过期")
    print(f"5. 如果不存在，创建一个新的API Key")
    print(f"6. 确保勾选了这些权限:")
    print(f"   ✅ Enable Reading")
    print(f"   ✅ Enable Futures")
    print(f"7. 复制新的API Key和Secret到 .env 文件")

if __name__ == "__main__":
    asyncio.run(diagnose())

