#!/usr/bin/env python3
"""测试第三方OpenAI兼容API连接"""

import sys
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai.llm_interface import TradingLLM
from src.config import settings


async def test_connection():
    """测试API连接"""
    print("=" * 60)
    print("第三方OpenAI兼容API连接测试")
    print("=" * 60)
    
    # 显示当前配置
    print("\n当前配置:")
    print(f"  API密钥: {settings.openai_api_key[:20]}..." if settings.openai_api_key else "  API密钥: 未设置")
    print(f"  Base URL: {settings.openai_base_url or '官方API (https://api.openai.com/v1)'}")
    
    if not settings.openai_api_key:
        print("\n❌ 错误：未设置OPENAI_API_KEY")
        print("请在.env文件中配置OPENAI_API_KEY")
        return False
    
    print("\n正在测试连接...")
    
    # 创建LLM实例
    llm = TradingLLM(
        primary_provider="openai",
        model="gpt-3.5-turbo"  # 使用便宜的模型测试
    )
    
    # 简单测试prompt
    test_prompt = """You are a helpful assistant. Please respond with a valid JSON object.

Task: Return a JSON object with a "status" field set to "ok" and a "message" field.

Output JSON only, no other text."""
    
    try:
        print("  发送测试请求...")
        response = await llm.decide(test_prompt)
        
        print("\n✅ API连接成功！")
        print(f"\n响应内容:")
        print(f"  {response}")
        
        return True
    
    except Exception as e:
        print(f"\n❌ API连接失败")
        print(f"\n错误信息: {e}")
        print("\n可能的原因:")
        print("  1. API密钥无效")
        print("  2. Base URL配置错误")
        print("  3. 网络连接问题")
        print("  4. API服务不可用")
        
        print("\n排查步骤:")
        print("  1. 检查.env文件中的OPENAI_API_KEY")
        print("  2. 检查OPENAI_BASE_URL是否正确")
        print("  3. 尝试使用curl测试:")
        
        base_url = settings.openai_base_url or "https://api.openai.com/v1"
        print(f"""
  curl -X POST "{base_url}/chat/completions" \\
    -H "Authorization: Bearer {settings.openai_api_key[:20]}..." \\
    -H "Content-Type: application/json" \\
    -d '{{"model":"gpt-3.5-turbo","messages":[{{"role":"user","content":"Hi"}}]}}'
        """)
        
        return False


async def test_models():
    """测试不同模型"""
    print("\n" + "=" * 60)
    print("测试不同模型")
    print("=" * 60)
    
    models = [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo-preview",
    ]
    
    simple_prompt = """Respond with JSON: {"test": "ok"}"""
    
    for model in models:
        print(f"\n测试模型: {model}")
        try:
            llm = TradingLLM(primary_provider="openai", model=model)
            response = await llm.decide(simple_prompt)
            print(f"  ✅ {model} 可用")
        except Exception as e:
            error_msg = str(e)
            if "model_not_found" in error_msg.lower() or "does not exist" in error_msg.lower():
                print(f"  ⚠️  {model} 不支持（API不提供此模型）")
            else:
                print(f"  ❌ {model} 失败: {error_msg[:100]}")


async def main():
    """主函数"""
    # 测试基本连接
    success = await test_connection()
    
    if success:
        # 测试不同模型
        try:
            await test_models()
        except KeyboardInterrupt:
            print("\n\n测试被用户中断")
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 测试完成！API配置正确")
        print("\n下一步:")
        print("  1. 根据支持的模型调整 config/trading_config.yaml")
        print("  2. 运行完整系统测试: python test_system.py")
        print("  3. 启动交易系统: python main.py")
    else:
        print("❌ 测试失败，请检查配置")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(0)

