"""LLM interface supporting multiple providers."""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional

from openai import OpenAI
from anthropic import Anthropic

from ..config import settings
from .output_parser import trading_parser, OutputParserException

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """
        Generate response from LLM.
        
        Returns:
            Dict with keys:
                - 'content': Main response text (required)
                - 'reasoning_content': Thinking/reasoning process (optional)
        """
        pass


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider (supports custom base_url for compatible APIs)."""
    
    def __init__(self, model: str = "gpt-4-turbo-preview", base_url: Optional[str] = None):
        # Support custom base_url for OpenAI-compatible APIs
        # e.g., OneAPI, vLLM, local deployments, etc.
        client_kwargs = {"api_key": settings.openai_api_key}
        
        # Use custom base_url if provided (env var or parameter)
        if base_url:
            client_kwargs["base_url"] = base_url
            # Using custom API silently
        elif settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
            # Using custom API from env silently
        
        self.client = OpenAI(**client_kwargs)
        self.model = model
        self.base_url = base_url or settings.openai_base_url
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """
        Generate response using OpenAI API.
        
        Supports optional kwargs:
            - temperature: float (default 0.3)
            - max_tokens: int (default 4000)
            - stream: bool (default True for reasoning extraction)
            - thinking_budget: int (for models that support it)
            - response_format: dict (e.g., {"type": "json_object"})
            - extra_body: dict (additional parameters)
        """
        try:
            temperature = kwargs.get('temperature', 0.3)
            max_tokens = kwargs.get('max_tokens', 4000)
            use_stream = kwargs.get('stream', True)
            
            # Build messages list
            messages = []
            
            # Add system message if provided
            if 'system' in kwargs:
                messages.append({
                    "role": "system",
                    "content": kwargs['system']
                })
            
            # Add user message
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            # Add optional parameters if provided
            if 'response_format' in kwargs:
                request_params["response_format"] = kwargs['response_format']
            
            if 'extra_body' in kwargs:
                request_params["extra_body"] = kwargs['extra_body']
            elif 'thinking_budget' in kwargs:
                # Convenience: auto-wrap thinking_budget in extra_body
                request_params["extra_body"] = {"thinking_budget": kwargs['thinking_budget']}
                # Using thinking_budget silently
            
            # Use streaming to capture reasoning_content (if available)
            if use_stream:
                request_params["stream"] = True
                response = self.client.chat.completions.create(**request_params)
                
                # Accumulate content and reasoning_content from stream
                content = ""
                reasoning_content = ""
                
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content += chunk.choices[0].delta.content
                    if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                        reasoning_content += chunk.choices[0].delta.reasoning_content
                
                result = {'content': content}
                if reasoning_content:
                    result['reasoning_content'] = reasoning_content
                    # Reasoning content extracted from stream silently
                
                return result
            
            else:
                # Non-streaming mode
                response = self.client.chat.completions.create(**request_params)
                message = response.choices[0].message
                
                result = {'content': message.content or ""}
                
                # Check if reasoning_content exists in the response
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    result['reasoning_content'] = message.reasoning_content
                    # Reasoning content extracted silently
                
                return result
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, model: str = "claude-3-opus-20240229"):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """Generate response using Anthropic API."""
        try:
            temperature = kwargs.get('temperature', 0.3)
            max_tokens = kwargs.get('max_tokens', 4000)
            
            # Use provided system prompt or default
            system_prompt = kwargs.get('system', "You are an expert cryptocurrency trader. Analyze market data and make trading decisions. Always output valid JSON only, no other text.")
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return {
                'content': message.content[0].text
            }
        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM provider (Ollama, vLLM, etc.)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:70b"):
        self.base_url = base_url
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> Dict:
        """Generate response using local LLM."""
        try:
            import aiohttp
            
            temperature = kwargs.get('temperature', 0.3)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "temperature": temperature,
                        "stream": False
                    }
                ) as response:
                    result = await response.json()
                    return {
                        'content': result['response']
                    }
        
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            raise


class TradingLLM:
    """
    Main LLM interface for trading decisions.
    Supports provider fallback and retry logic.
    Supports both reasoning models (one-step) and regular models (two-step).
    """
    
    def __init__(
        self,
        primary_provider: str = "openai",
        model: Optional[str] = None,
        fallback_provider: Optional[str] = None,
        base_url: Optional[str] = None,
        is_reasoning_model: bool = True
    ):
        self.primary = self._get_provider(primary_provider, model, base_url)
        self.fallback = self._get_provider(fallback_provider, model, base_url) if fallback_provider else None
        self.is_reasoning_model = is_reasoning_model
        # Model initialization logged silently
    
    def _get_provider(self, provider_name: str, model: Optional[str], base_url: Optional[str] = None) -> BaseLLMProvider:
        """Get LLM provider instance."""
        if provider_name == "openai":
            return OpenAIProvider(
                model=model or "gpt-4-turbo-preview",
                base_url=base_url
            )
        elif provider_name == "anthropic":
            return AnthropicProvider(model or "claude-3-opus-20240229")
        elif provider_name == "local":
            return LocalLLMProvider(model=model or "llama3.1:70b")
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    async def decide(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict:
        """
        Generate trading decision from prompt using Langchain + Pydantic parser.
        
        For reasoning models (DeepSeek-R1, o1): One-step generation with built-in reasoning
        For regular models (GPT-4, Claude): Two-step process:
            1. Generate thinking/analysis
            2. Generate JSON decision with context from step 1
        
        Args:
            prompt: Formatted trading prompt
            max_retries: Number of retries on failure
            **kwargs: Additional parameters for LLM
        
        Returns:
            Dict with keys:
                - 'decisions': Parsed and validated decision dict (coin -> decision)
                - 'thinking': AI reasoning/thinking process (if available)
                - 'raw_response': Raw LLM response text
        """
        # Check if this is a reasoning model or regular model
        if self.is_reasoning_model:
            # Reasoning model: One-step process (existing logic)
            return await self._decide_one_step(prompt, max_retries, **kwargs)
        else:
            # Regular model: Two-step process (new logic)
            return await self._decide_two_step(prompt, max_retries, **kwargs)
    
    async def _decide_one_step(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict:
        """
        One-step decision for reasoning models (e.g., DeepSeek-R1, o1).
        Model generates thinking + JSON in single call.
        """
        for attempt in range(max_retries):
            try:
                # Try primary provider (returns Dict with 'content' and optionally 'reasoning_content')
                response_dict = await self.primary.generate(prompt, **kwargs)
                
                # Extract content and reasoning_content
                response_text = response_dict.get('content', '')
                reasoning_from_api = response_dict.get('reasoning_content', '')
                
                # Extract thinking: prioritize reasoning_content from API, fallback to parsing tags
                thinking = ""
                if reasoning_from_api:
                    thinking = reasoning_from_api
                    # Reasoning content extracted silently
                else:
                    thinking = self._extract_thinking(response_text)
                    if thinking:
                        pass  # Thinking extracted from tags silently
                    else:
                        logger.warning("⚠️ No reasoning_content or <think> tags found!")
                
                if thinking:
                    pass  # Thinking preview shown by trading loop
                
                # Parse and validate with Langchain + Pydantic
                decisions = self._parse_with_pydantic(response_text)
                
                # Decision validated successfully
                
                # Return decisions with thinking and raw response
                return {
                    'decisions': decisions,
                    'thinking': thinking,
                    'raw_response': response_text[:1000]  # First 1000 chars
                }
            
            except OutputParserException as e:
                logger.warning(f"❌ Parsing failed (attempt {attempt + 1}): {e}")
                logger.debug(f"Response text: {response_text[:500]}...")
                
                # Try fallback provider
                if self.fallback and attempt == max_retries - 1:
                    try:
                        logger.warning("⚠️ Trying fallback provider...")
                        fallback_dict = await self.fallback.generate(prompt, **kwargs)
                        fallback_text = fallback_dict.get('content', '')
                        fallback_thinking = fallback_dict.get('reasoning_content', '') or self._extract_thinking(fallback_text)
                        decision = self._parse_with_pydantic(fallback_text)
                        logger.info("✅ Fallback provider succeeded")
                        return {
                            'decisions': decision,
                            'thinking': fallback_thinking,
                            'raw_response': fallback_text[:1000]
                        }
                    except Exception as fallback_error:
                        logger.error(f"❌ Fallback provider also failed: {fallback_error}")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    # Last attempt failed, try legacy parser as fallback
                    logger.warning("⚠️ All Pydantic parsing attempts failed, trying legacy parser...")
                    try:
                        legacy_result = self._parse_response_legacy(response_text)
                        return {
                            'decisions': legacy_result,
                            'thinking': thinking,  # Use previously extracted thinking
                            'raw_response': response_text[:1000]
                        }
                    except Exception as legacy_error:
                        logger.error(f"❌ Legacy parser also failed: {legacy_error}")
                        raise e  # Raise original parsing exception
            
            except Exception as e:
                logger.error(f"❌ LLM generation failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise
        
        raise RuntimeError("All LLM attempts failed")
    
    async def _decide_two_step(
        self,
        prompt: str,
        max_retries: int = 3,
        **kwargs
    ) -> Dict:
        """
        Two-step decision for regular models (e.g., GPT-4, Claude).
        Step 1: Generate thinking/analysis
        Step 2: Generate JSON decision with context from step 1
        """
        logger.info("🧠 Using TWO-STEP process (regular model)")
        
        for attempt in range(max_retries):
            try:
                # STEP 1: Ask model to think and analyze
                logger.info(f"📝 STEP 1/2: Requesting thinking/analysis (attempt {attempt + 1})")
                thinking_prompt = self._build_thinking_prompt(prompt)
                
                # Get thinking response
                thinking_dict = await self.primary.generate(thinking_prompt, **kwargs)
                thinking_text = thinking_dict.get('content', '')
                
                if not thinking_text or len(thinking_text) < 50:
                    logger.warning(f"⚠️ Thinking response too short: {len(thinking_text)} chars")
                    if attempt < max_retries - 1:
                        logger.info(f"🔄 Retrying step 1... (attempt {attempt + 2}/{max_retries})")
                        continue
                
                logger.info(f"✅ Step 1 complete: {len(thinking_text)} characters of thinking")
                logger.info(f"💭 Thinking preview: {thinking_text[:300]}...")
                
                # STEP 2: Ask model to generate JSON decision based on thinking
                logger.info(f"📊 STEP 2/2: Requesting JSON decision with context (attempt {attempt + 1})")
                decision_prompt = self._build_decision_prompt(prompt, thinking_text)
                
                # Get decision response
                decision_dict = await self.primary.generate(decision_prompt, **kwargs)
                decision_text = decision_dict.get('content', '')
                
                # Parse and validate with Langchain + Pydantic
                decisions = self._parse_with_pydantic(decision_text)
                
                logger.info(f"✅ Two-step LLM decision complete (attempt {attempt + 1})")
                
                # Return decisions with thinking from step 1
                return {
                    'decisions': decisions,
                    'thinking': thinking_text,  # Thinking from step 1
                    'raw_response': decision_text[:1000]  # Decision JSON from step 2
                }
            
            except OutputParserException as e:
                logger.warning(f"❌ Step 2 parsing failed (attempt {attempt + 1}): {e}")
                logger.debug(f"Decision response: {decision_text[:500]}...")
                
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying two-step process... (attempt {attempt + 2}/{max_retries})")
                else:
                    # Last attempt failed, try legacy parser
                    logger.warning("⚠️ All parsing attempts failed, trying legacy parser...")
                    try:
                        legacy_result = self._parse_response_legacy(decision_text)
                        return {
                            'decisions': legacy_result,
                            'thinking': thinking_text,
                            'raw_response': decision_text[:1000]
                        }
                    except Exception as legacy_error:
                        logger.error(f"❌ Legacy parser also failed: {legacy_error}")
                        raise e
            
            except Exception as e:
                logger.error(f"❌ Two-step process failed (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"🔄 Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise
        
        raise RuntimeError("All two-step LLM attempts failed")
    
    def _build_thinking_prompt(self, original_prompt: str) -> str:
        """
        Build prompt for step 1: asking model to think and analyze.
        
        Args:
            original_prompt: The original trading prompt with market data
            
        Returns:
            Prompt for thinking step
        """
        thinking_prompt = f"""{original_prompt}

========================================
STEP 1: THINKING AND ANALYSIS
========================================

Please analyze the market data above and think through your trading strategy.

Consider the following in your analysis:
1. Market trends for each coin (bullish, bearish, sideways)
2. Technical indicators (RSI, MACD, EMA crossovers, volume)
3. Risk/reward ratios for potential trades
4. Current positions and portfolio balance
5. Market sentiment and volatility

DO NOT output JSON yet. Just provide your detailed thinking and analysis in natural language.

Your analysis:"""
        
        return thinking_prompt
    
    def _build_decision_prompt(self, original_prompt: str, thinking: str) -> str:
        """
        Build prompt for step 2: asking model to output JSON decision.
        
        Args:
            original_prompt: The original trading prompt with market data
            thinking: The thinking/analysis from step 1
            
        Returns:
            Prompt for decision step
        """
        decision_prompt = f"""{original_prompt}

========================================
YOUR PREVIOUS ANALYSIS (STEP 1)
========================================

{thinking}

========================================
STEP 2: GENERATE JSON DECISION
========================================

Based on your analysis above, now output your trading decisions in the required JSON format.

Follow the output format instructions provided in the original prompt above.

Your JSON decision:"""
        
        return decision_prompt
    
    def _extract_thinking(self, response_text: str) -> str:
        """
        Extract AI thinking/reasoning process from response.
        
        Some models (like DeepSeek-R1, o1) wrap their reasoning in tags:
        - <think>...</think>
        - <reasoning>...</reasoning>
        
        Args:
            response_text: Raw LLM response
            
        Returns:
            Extracted thinking text, or empty string if not found
        """
        import re
        
        # Try <think>...</think> tags
        think_match = re.search(r'<think>(.*?)</think>', response_text, re.DOTALL)
        if think_match:
            return think_match.group(1).strip()
        
        # Try <reasoning>...</reasoning> tags
        reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', response_text, re.DOTALL)
        if reasoning_match:
            return reasoning_match.group(1).strip()
        
        # No thinking tags found
        return ""
    
    def _parse_with_pydantic(self, response_text: str) -> Dict:
        """
        Parse LLM response using Langchain + Pydantic (NEW METHOD).
        
        Args:
            response_text: Raw response from LLM
            
        Returns:
            Validated dict with trade_signal_args format
            
        Raises:
            OutputParserException: If parsing/validation fails
        """
        try:
            # Use Langchain parser with Pydantic validation
            decisions = trading_parser.parse(response_text)
            
            logger.info(f"📊 Pydantic validation passed: {len(decisions)} coins")
            for coin, decision in list(decisions.items())[:3]:
                logger.debug(f"  ✓ {coin}: {decision.get('trade_signal_args', {}).get('signal', 'unknown')}")
            
            return decisions
            
        except Exception as e:
            logger.error(f"Pydantic parsing error: {e}")
            raise OutputParserException(f"Failed to parse with Pydantic: {e}")
    
    def _parse_response_legacy(self, response_text: str) -> Dict:
        """
        LEGACY: Parse LLM response to JSON (fallback method).
        
        This is kept for backward compatibility only.
        """
        logger.warning("⚠️ Using legacy JSON parser (no Pydantic validation)")
        return self._parse_response(response_text)
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response to JSON."""
        try:
            # Step 1: Remove reasoning/thinking tags (for reasoning models like o1)
            if "<think>" in response_text and "</think>" in response_text:
                import re
                response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
            
            # Step 2: Try to extract JSON from text (更强力的提取)
            import re
            
            # 方法1: 查找 ```json 代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1).strip()
            
            # 方法2: 查找普通 ``` 代码块中的JSON
            elif '```' in response_text:
                json_start = response_text.find("```")
                json_end = response_text.find("```", json_start + 3)
                if json_end != -1:
                    potential_json = response_text[json_start + 3:json_end].strip()
                    # 如果是JSON格式（以{开头）
                    if potential_json.startswith('{'):
                        response_text = potential_json
            
            # 方法3: 查找JSON对象（最外层的大括号）
            else:
                # 查找第一个 { 到最后一个 } 之间的内容
                first_brace = response_text.find('{')
                if first_brace != -1:
                    # 从后往前找最后一个 }
                    last_brace = response_text.rfind('}')
                    if last_brace != -1 and last_brace > first_brace:
                        potential_json = response_text[first_brace:last_brace + 1]
                        # 验证是否是有效的JSON结构
                        if potential_json.count('{') == potential_json.count('}'):
                            response_text = potential_json
            
            # Step 3: Clean up whitespace and common issues
            response_text = response_text.strip()
            # 移除可能的markdown格式
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```\s*$', '', response_text)
            
            # Step 4: Parse JSON
            decision = json.loads(response_text)
            
            # Step 5: Validate structure
            if not isinstance(decision, dict):
                raise ValueError(f"Expected dict, got {type(decision)}")
            
            return decision
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}...")
            logger.error(f"Response text (last 200 chars): ...{response_text[-200:]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

