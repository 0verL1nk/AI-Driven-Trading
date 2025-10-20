#!/usr/bin/env python3
"""检查配置文件是否正确设置"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings, trading_config


def check_env_vars():
    """检查环境变量"""
    print("🔍 检查环境变量...")
    
    issues = []
    
    # 检查必需的API密钥
    if settings.enable_paper_trading:
        print("  ✓ 模拟交易模式（Paper Trading）")
    else:
        print("  ⚠️  真实交易模式（Live Trading）")
        if not settings.binance_api_key:
            issues.append("缺少 BINANCE_API_KEY")
        if not settings.binance_api_secret:
            issues.append("缺少 BINANCE_API_SECRET")
    
    # 检查AI API密钥
    if trading_config.ai_provider == "openai":
        if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
            issues.append("缺少有效的 OPENAI_API_KEY")
        else:
            print(f"  ✓ OpenAI API密钥已设置")
    
    elif trading_config.ai_provider == "anthropic":
        if not settings.anthropic_api_key:
            issues.append("缺少 ANTHROPIC_API_KEY")
        else:
            print(f"  ✓ Anthropic API密钥已设置")
    
    return issues


def check_trading_config():
    """检查交易配置"""
    print("\n🔍 检查交易配置...")
    
    issues = []
    
    # 检查交易对
    if not trading_config.trading_pairs:
        issues.append("trading_pairs 为空")
    else:
        print(f"  ✓ 交易对: {len(trading_config.trading_pairs)} 个")
        for pair in trading_config.trading_pairs:
            print(f"    - {pair}")
    
    # 检查AI配置
    print(f"  ✓ AI提供商: {trading_config.ai_provider}")
    print(f"  ✓ AI模型: {trading_config.ai_model}")
    print(f"  ✓ 决策间隔: {trading_config.decision_interval_minutes} 分钟")
    
    # 检查决策间隔合理性
    if trading_config.decision_interval_minutes < 1:
        issues.append(f"决策间隔过短（{trading_config.decision_interval_minutes}分钟），可能导致过高API费用")
    
    return issues


def check_risk_params():
    """检查风险参数"""
    print("\n🔍 检查风险参数...")
    
    issues = []
    
    risk = trading_config.risk_params
    
    # 仓位管理
    max_risk = risk['position_sizing']['max_risk_per_trade_percent']
    print(f"  ✓ 单笔最大风险: {max_risk}%")
    
    if max_risk > 5:
        issues.append(f"单笔风险 {max_risk}% 过高，建议 ≤ 2%")
    
    # 杠杆
    min_lev = risk['leverage']['min']
    max_lev = risk['leverage']['max']
    print(f"  ✓ 杠杆范围: {min_lev}x - {max_lev}x")
    
    if max_lev > 20:
        issues.append(f"最大杠杆 {max_lev}x 过高，建议 ≤ 15x")
    
    # 回撤保护
    max_dd = risk['drawdown_protection']['max_daily_drawdown_percent']
    print(f"  ✓ 最大日回撤: {max_dd}%")
    
    # 风险回报比
    min_rr = risk['exit_strategy']['min_risk_reward_ratio']
    print(f"  ✓ 最小风险回报比: {min_rr}:1")
    
    if min_rr < 1.5:
        issues.append(f"风险回报比 {min_rr} 过低，建议 ≥ 1.5")
    
    return issues


def main():
    """主函数"""
    print("=" * 60)
    print("配置检查工具")
    print("=" * 60)
    
    all_issues = []
    
    # 检查各项配置
    all_issues.extend(check_env_vars())
    all_issues.extend(check_trading_config())
    all_issues.extend(check_risk_params())
    
    # 输出结果
    print("\n" + "=" * 60)
    
    if all_issues:
        print("❌ 发现以下问题：\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"{i}. {issue}")
        print("\n请修复这些问题后再运行系统。")
        sys.exit(1)
    else:
        print("✅ 所有配置检查通过！")
        print("\n系统已准备就绪，可以运行：")
        print("  python main.py")
        sys.exit(0)


if __name__ == "__main__":
    main()

