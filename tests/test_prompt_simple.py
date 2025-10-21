#!/usr/bin/env python3
"""
完整Prompt测试 - 查看完整构建后的AI提示词
"""
import sys
from pathlib import Path
import asyncio
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.prompt_builder import PromptBuilder
from src.ai.output_parser import trading_parser


def print_section(title: str, content: str, max_lines: int = None):
    """美化打印"""
    print("\n" + "=" * 100)
    print(f"📋 {title}")
    print("=" * 100)
    if max_lines:
        lines = content.split('\n')
        if len(lines) > max_lines:
            print('\n'.join(lines[:max_lines]))
            print(f"\n... ({len(lines) - max_lines} more lines) ...")
            print('\n'.join(lines[-10:]))  # 显示最后10行
        else:
            print(content)
    else:
        print(content)
    print("=" * 100)


def generate_mock_market_data(coin: str) -> dict:
    """生成模拟市场数据"""
    # 生成3分钟K线数据（最近10根）
    now = datetime.now()
    dates = [now - timedelta(minutes=3*i) for i in range(10, 0, -1)]
    
    base_price = {'BTC': 95000, 'ETH': 3500, 'SOL': 180, 'BNB': 600, 'XRP': 2.5, 'DOGE': 0.35}[coin]
    
    intraday_data = {
        'timestamp': dates,
        'open': [base_price + i*10 for i in range(10)],
        'high': [base_price + i*10 + 50 for i in range(10)],
        'low': [base_price + i*10 - 50 for i in range(10)],
        'close': [base_price + i*10 + 20 for i in range(10)],
        'volume': [100 + i*5 for i in range(10)],
    }
    
    intraday_df = pd.DataFrame(intraday_data)
    
    # 添加指标
    intraday_df['ema_20'] = intraday_df['close'].rolling(window=5).mean()
    intraday_df['ema_50'] = intraday_df['close'].rolling(window=8).mean()
    intraday_df['macd'] = [50 + i*2 for i in range(10)]
    intraday_df['rsi_7'] = [50 + i for i in range(10)]
    intraday_df['rsi_14'] = [52 + i for i in range(10)]
    intraday_df['atr_14'] = [100 for _ in range(10)]
    
    # 生成4小时K线数据
    longterm_dates = [now - timedelta(hours=4*i) for i in range(10, 0, -1)]
    longterm_data = {
        'timestamp': longterm_dates,
        'open': [base_price + i*100 for i in range(10)],
        'high': [base_price + i*100 + 200 for i in range(10)],
        'low': [base_price + i*100 - 200 for i in range(10)],
        'close': [base_price + i*100 + 50 for i in range(10)],
        'volume': [1000 + i*50 for i in range(10)],
    }
    
    longterm_df = pd.DataFrame(longterm_data)
    longterm_df['ema_20'] = longterm_df['close'].rolling(window=5).mean()
    longterm_df['ema_50'] = longterm_df['close'].rolling(window=8).mean()
    longterm_df['macd'] = [100 + i*5 for i in range(10)]
    longterm_df['rsi_14'] = [55 + i for i in range(10)]
    longterm_df['atr_14'] = [200 for _ in range(10)]
    
    return {
        'intraday_df': intraday_df,
        'longterm_df': longterm_df,
        'funding_rate': 0.0001,
        'open_interest': 1000000,
        'oi_average': 950000
    }


def test_full_prompt_no_positions():
    """测试完整Prompt - 无持仓"""
    print("\n" + "🔍 TEST: 完整Prompt构建 - 无持仓情况".center(100, "="))
    
    pb = PromptBuilder()
    
    # 账户状态
    account_state = {
        'total_value': 10000.0,
        'total_return': 0.0,
        'cash': 10000.0,
        'sharpe_ratio': 0.0,
        'num_positions': 0
    }
    
    positions = []
    
    # 生成所有币种的市场数据
    market_data = {}
    for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']:
        market_data[coin] = generate_mock_market_data(coin)
    
    # 构建完整prompt
    full_prompt = pb.build_trading_prompt(
        market_data=market_data,
        account_state=account_state,
        positions=positions
    )
    
    # 显示prompt统计
    print(f"\n📊 Prompt 统计:")
    print(f"   总长度: {len(full_prompt)} 字符")
    print(f"   总行数: {len(full_prompt.split(chr(10)))} 行")
    print(f"   预估tokens: ~{len(full_prompt) // 4} tokens")
    
    # 显示部分内容（前50行和后50行）
    print_section("PROMPT 预览 (前50行 + 后50行)", full_prompt, max_lines=50)
    
    return full_prompt


def test_full_prompt_with_positions():
    """测试完整Prompt - 有持仓"""
    print("\n" + "🔍 TEST: 完整Prompt构建 - 有持仓情况".center(100, "="))
    
    pb = PromptBuilder()
    
    # 账户状态
    account_state = {
        'total_value': 10500.0,
        'total_return': 5.0,
        'cash': 5000.0,
        'sharpe_ratio': 1.8,
        'num_positions': 2
    }
    
    positions = [
        {
            'symbol': 'BTC',
            'side': 'LONG',
            'size': 0.05,
            'entry_price': 95000.0,
            'current_price': 96000.0,
            'pnl': 50.0,
            'pnl_percent': 1.05,
            'leverage': 10,
            'stop_loss': 93000.0,
            'take_profit': 99000.0,
            'invalidation_condition': 'If price closes below 92000 on 3-min candle'
        },
        {
            'symbol': 'ETH',
            'side': 'LONG',
            'size': 1.5,
            'entry_price': 3500.0,
            'current_price': 3550.0,
            'pnl': 75.0,
            'pnl_percent': 1.43,
            'leverage': 12,
            'stop_loss': 3400.0,
            'take_profit': 3700.0,
            'invalidation_condition': 'If price closes below 3350 on 3-min candle'
        }
    ]
    
    # 生成所有币种的市场数据
    market_data = {}
    for coin in ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE']:
        market_data[coin] = generate_mock_market_data(coin)
    
    # 构建完整prompt
    full_prompt = pb.build_trading_prompt(
        market_data=market_data,
        account_state=account_state,
        positions=positions
    )
    
    # 显示prompt统计
    print(f"\n📊 Prompt 统计:")
    print(f"   总长度: {len(full_prompt)} 字符")
    print(f"   总行数: {len(full_prompt.split(chr(10)))} 行")
    print(f"   预估tokens: ~{len(full_prompt) // 4} tokens")
    
    # 显示部分内容
    print_section("PROMPT 预览 (前50行 + 后50行)", full_prompt, max_lines=50)
    
    return full_prompt


def test_no_positions():
    """测试场景1：无持仓情况"""
    print("\n" + "🔍 TEST 1: 无持仓情况".center(100, "="))
    
    pb = PromptBuilder()
    
    account_state = {
        'total_value': 5000.0,
        'total_return': 0.0,
        'cash': 5000.0,
        'sharpe_ratio': 0.0,
        'num_positions': 0
    }
    
    positions = []  # 空持仓
    
    account_section = pb._format_account_section(account_state, positions)
    
    print_section("ACCOUNT SECTION (无持仓)", account_section)
    
    # 检查关键内容
    print("\n📊 检查结果:")
    checks = [
        ("包含'No current positions'", "No current positions" in account_section),
        ("包含格式说明", "format" in account_section.lower() or "json" in account_section.lower()),
        ("包含CRITICAL规则", "CRITICAL" in account_section),
        ("禁止hold信号", "hold" in account_section and "close_position" in account_section),
    ]
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    return account_section


def test_with_positions():
    """测试场景2：有持仓情况"""
    print("\n" + "🔍 TEST 2: 有持仓情况".center(100, "="))
    
    pb = PromptBuilder()
    
    account_state = {
        'total_value': 5500.0,
        'total_return': 0.10,
        'cash': 500.0,
        'sharpe_ratio': 1.5,
        'num_positions': 1
    }
    
    positions = [
        {
            'symbol': 'BTC',
            'side': 'LONG',
            'size': 0.05,
            'entry_price': 105000.0,
            'current_price': 109500.0,
            'pnl': 225.0,
            'pnl_percent': 4.29,
            'leverage': 10
        }
    ]
    
    account_section = pb._format_account_section(account_state, positions)
    
    print_section("ACCOUNT SECTION (有持仓)", account_section)
    
    # 检查关键内容
    print("\n📊 检查结果:")
    checks = [
        ("包含持仓信息", "Current live positions" in account_section),
        ("包含BTC持仓", "BTC" in account_section),
        ("包含格式说明", "format" in account_section.lower() or "json" in account_section.lower()),
    ]
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
    
    return account_section


def test_format_instructions():
    """测试场景3：检查格式说明"""
    print("\n" + "🔍 TEST 3: 格式说明详细检查".center(100, "="))
    
    format_instructions = trading_parser.get_format_instructions()
    
    print_section("FORMAT INSTRUCTIONS", format_instructions)
    
    # 检查关键元素
    print("\n📊 格式说明完整性检查:")
    checks = [
        ("包含JSON schema", '"type": "object"' in format_instructions),
        ("包含signal枚举", '"enum"' in format_instructions and 'entry' in format_instructions),
        ("包含CRITICAL规则", "CRITICAL:" in format_instructions or "CRITICAL" in format_instructions),
        ("明确说明无持仓时的限制", "no existing position" in format_instructions.lower() or "no current position" in format_instructions.lower()),
        ("允许省略no_action", "OMIT" in format_instructions or "omit" in format_instructions),
        ("包含示例", "Example" in format_instructions or "example" in format_instructions.lower()),
    ]
    
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")


def main():
    """主测试函数"""
    print("\n" + "🚀 完整 AI PROMPT 查看工具".center(100, "="))
    print("目的: 查看完整构建后的AI提示词，包含市场数据、账户信息、风险规则等\n")
    
    # 测试完整prompt - 无持仓
    print("\n" + "1️⃣  构建无持仓情况的完整Prompt".center(100, "-"))
    full_prompt_1 = test_full_prompt_no_positions()
    
    # 测试完整prompt - 有持仓
    print("\n" + "2️⃣  构建有持仓情况的完整Prompt".center(100, "-"))
    full_prompt_2 = test_full_prompt_with_positions()
    
    # 保存完整prompt到文件
    output_dir = Path(__file__).parent / "logs"
    output_dir.mkdir(exist_ok=True)
    
    file1 = output_dir / "full_prompt_no_positions.txt"
    file2 = output_dir / "full_prompt_with_positions.txt"
    
    with open(file1, "w", encoding="utf-8") as f:
        f.write(full_prompt_1)
    
    with open(file2, "w", encoding="utf-8") as f:
        f.write(full_prompt_2)
    
    print("\n" + "=" * 100)
    print("💾 完整Prompt已保存到:")
    print(f"   📄 {file1}")
    print(f"   📄 {file2}")
    print("\n💡 提示: 用文本编辑器打开查看完整内容")
    print("=" * 100)
    
    # 内容分析
    print("\n" + "📊 Prompt 结构分析".center(100, "="))
    
    # 提取关键部分
    sections = {
        "市场数据部分": "ALL BTC DATA" in full_prompt_1,
        "账户信息部分": "HERE IS YOUR ACCOUNT INFORMATION" in full_prompt_1,
        "风险管理规则": "RISK MANAGEMENT RULES" in full_prompt_1,
        "风险回报比计算": "Risk/Reward Ratio = Reward / Risk" in full_prompt_1,
        "格式说明": "OUTPUT FORMAT INSTRUCTIONS" in full_prompt_1,
        "具体数值示例": "EXAMPLE (LONG BTC" in full_prompt_1,
        "最大风险金额": "$" in full_prompt_1 and "maximum risk" in full_prompt_1.lower(),
    }
    
    print("\n✅ 关键部分检查:")
    for section_name, exists in sections.items():
        status = "✅" if exists else "❌"
        print(f"{status} {section_name}")
    
    # 对比两个prompt
    print(f"\n📏 Prompt大小对比:")
    print(f"   无持仓: {len(full_prompt_1):,} 字符 (~{len(full_prompt_1)//4:,} tokens)")
    print(f"   有持仓: {len(full_prompt_2):,} 字符 (~{len(full_prompt_2)//4:,} tokens)")
    print(f"   差异: {abs(len(full_prompt_2) - len(full_prompt_1)):,} 字符")
    
    print("\n" + "=" * 100)


if __name__ == "__main__":
    main()

