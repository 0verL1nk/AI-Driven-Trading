#!/usr/bin/env python3
"""生成示例Prompt用于测试"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.prompt_builder import PromptBuilder
from src.data.indicator_engine import IndicatorEngine


def create_sample_data(coin='BTC', start_price=110000):
    """创建示例市场数据"""
    engine = IndicatorEngine()
    
    # 创建100根3分钟K线
    data_3m = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='3min'),
        'open': [start_price + i * 10 for i in range(100)],
        'high': [start_price + i * 10 + 50 for i in range(100)],
        'low': [start_price + i * 10 - 50 for i in range(100)],
        'close': [start_price + i * 10 + 20 for i in range(100)],
        'volume': [1000 + i * 5 for i in range(100)]
    }
    df_3m = pd.DataFrame(data_3m)
    df_3m = engine.add_all_indicators(df_3m)
    
    # 创建100根4小时K线
    data_4h = {
        'timestamp': pd.date_range('2024-01-01', periods=100, freq='4H'),
        'open': [start_price + i * 100 for i in range(100)],
        'high': [start_price + i * 100 + 200 for i in range(100)],
        'low': [start_price + i * 100 - 200 for i in range(100)],
        'close': [start_price + i * 100 + 50 for i in range(100)],
        'volume': [5000 + i * 20 for i in range(100)]
    }
    df_4h = pd.DataFrame(data_4h)
    df_4h = engine.add_all_indicators(df_4h)
    
    return {
        'intraday_df': df_3m,
        'longterm_df': df_4h,
        'funding_rate': -0.0001,
        'open_interest': 27000.0,
        'oi_average': 26500.0
    }


def main():
    """生成示例Prompt"""
    print("生成示例Prompt...\n")
    
    builder = PromptBuilder()
    
    # 创建6种币的示例数据
    market_data = {
        'BTC': create_sample_data('BTC', 110000),
        'ETH': create_sample_data('ETH', 3950),
        'SOL': create_sample_data('SOL', 189),
        'BNB': create_sample_data('BNB', 1100),
        'XRP': create_sample_data('XRP', 2.46),
        'DOGE': create_sample_data('DOGE', 0.198)
    }
    
    # 示例账户状态
    account_state = {
        'total_return': 15.5,
        'cash': 8500.0,
        'total_value': 11550.0,
        'sharpe_ratio': 0.82
    }
    
    # 示例持仓
    positions = [
        {
            'symbol': 'BTC',
            'quantity': 0.1,
            'entry_price': 108000,
            'current_price': 110900,
            'liquidation_price': 97000,
            'unrealized_pnl': 290,
            'leverage': 10,
            'exit_plan': {
                'profit_target': 115000,
                'stop_loss': 106000,
                'invalidation_condition': 'If the price closes below 105000 on a 3-minute candle'
            },
            'confidence': 0.75,
            'risk_usd': 200,
            'sl_oid': 12345,
            'tp_oid': 12346,
            'wait_for_fill': False,
            'entry_oid': 12344,
            'notional_usd': 11090
        }
    ]
    
    # 构建Prompt
    prompt = builder.build_trading_prompt(
        market_data=market_data,
        account_state=account_state,
        positions=positions
    )
    
    # 保存到文件
    output_path = Path(__file__).parent.parent / 'logs' / 'sample_prompt.txt'
    output_path.parent.mkdir(exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"✅ Prompt已生成并保存到: {output_path}")
    print(f"\nPrompt长度: {len(prompt)} 字符")
    print(f"Token估算: ~{len(prompt) // 4} tokens")
    print("\n前500字符预览:")
    print("-" * 60)
    print(prompt[:500])
    print("-" * 60)
    print("\n您可以将此Prompt发送给GPT-4测试AI决策功能。")


if __name__ == "__main__":
    main()

