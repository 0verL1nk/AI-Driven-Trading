#!/usr/bin/env python3
"""
测试AI返回的简化no_action格式是否能正确处理
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.decision_models import CoinDecision, TradingDecisions
from src.ai.output_parser import TradingDecisionParser

def test_simplified_no_action():
    """测试简化的no_action格式（只有coin和signal）"""
    print("\n" + "=" * 80)
    print("测试1: 简化的no_action格式（用户提供的例子）")
    print("=" * 80)
    
    # 用户提供的格式
    user_data = {
        "ETH": {
            "coin": "ETH",
            "signal": "entry",
            "leverage": 10,
            "confidence": 0.7,
            "risk_usd": 100.36,
            "profit_target": 3886.95,
            "stop_loss": 3866.05,
            "invalidation_condition": "If price closes below 3866.05"
        },
        "SOL": {
            "coin": "SOL",
            "signal": "no_action"
        },
        "BTC": {
            "coin": "BTC",
            "signal": "no_action"
        },
        "BNB": {
            "coin": "BNB",
            "signal": "no_action"
        }
    }
    
    try:
        # 测试每个币种
        for coin, data in user_data.items():
            print(f"\n处理 {coin}:")
            print(f"  输入: {data}")
            
            decision = CoinDecision(**data)
            print(f"  ✅ 验证成功!")
            print(f"  Signal: {decision.signal}")
            print(f"  Leverage: {decision.leverage} (auto-filled)" if decision.leverage else f"  Leverage: None")
            print(f"  Confidence: {decision.confidence} (auto-filled)" if decision.confidence else f"  Confidence: None")
            print(f"  Risk USD: {decision.risk_usd} (auto-filled)" if decision.risk_usd is not None else f"  Risk USD: None")
            
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        return False
    
    return True


def test_complete_trading_decisions():
    """测试完整的TradingDecisions对象"""
    print("\n" + "=" * 80)
    print("测试2: 完整的TradingDecisions验证")
    print("=" * 80)
    
    user_data = {
        "ETH": {
            "coin": "ETH",
            "signal": "entry",
            "leverage": 10,
            "confidence": 0.7,
            "risk_usd": 100.36,
            "profit_target": 3886.95,
            "stop_loss": 3866.05,
            "invalidation_condition": "If price closes below 3866.05"
        },
        "SOL": {
            "coin": "SOL",
            "signal": "no_action"
        },
        "BTC": {
            "coin": "BTC",
            "signal": "no_action"
        }
    }
    
    try:
        decisions = TradingDecisions(**user_data)
        print("✅ TradingDecisions验证成功!")
        
        # 转换为dict格式
        result_dict = decisions.to_dict()
        print(f"\n转换后的格式 (带trade_signal_args包装):")
        for coin, decision in result_dict.items():
            print(f"\n{coin}:")
            for key, value in decision['trade_signal_args'].items():
                print(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parser_integration():
    """测试与output_parser的集成"""
    print("\n" + "=" * 80)
    print("测试3: 与TradingDecisionParser集成测试")
    print("=" * 80)
    
    # 模拟AI返回的JSON字符串
    ai_response = """{
  "ETH": {
    "coin": "ETH",
    "signal": "entry",
    "leverage": 10,
    "confidence": 0.7,
    "risk_usd": 100.36,
    "profit_target": 3886.95,
    "stop_loss": 3866.05,
    "invalidation_condition": "If price closes below 3866.05"
  },
  "SOL": {
    "coin": "SOL",
    "signal": "no_action"
  },
  "BTC": {
    "coin": "BTC",
    "signal": "no_action"
  }
}"""
    
    try:
        parser = TradingDecisionParser()
        result = parser.parse(ai_response)
        
        print("✅ Parser解析成功!")
        print(f"\n解析结果: {len(result)} 个币种")
        for coin, decision in result.items():
            signal = decision.get('trade_signal_args', {}).get('signal', 'unknown')
            print(f"  {coin}: {signal}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🧪 简化no_action格式兼容性测试".center(80, "="))
    
    results = []
    
    # 测试1: 简化格式
    results.append(("简化no_action格式", test_simplified_no_action()))
    
    # 测试2: 完整验证
    results.append(("TradingDecisions对象", test_complete_trading_decisions()))
    
    # 测试3: Parser集成
    results.append(("Parser集成", test_parser_integration()))
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结".center(80))
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 所有测试通过! 简化no_action格式可以正确处理。")
    else:
        print("\n⚠️ 部分测试失败，需要修复。")
    
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())

