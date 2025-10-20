"""LLM interface supporting multiple providers."""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Optional

from openai import OpenAI
from anthropic import Anthropic

from ..config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response from LLM."""
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
            logger.info(f"Using custom OpenAI-compatible API: {base_url}")
        elif settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
            logger.info(f"Using custom OpenAI-compatible API from env: {settings.openai_base_url}")
        
        self.client = OpenAI(**client_kwargs)
        self.model = model
        self.base_url = base_url or settings.openai_base_url
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using OpenAI API."""
        try:
            temperature = kwargs.get('temperature', 0.3)
            max_tokens = kwargs.get('max_tokens', 4000)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert cryptocurrency trader. Analyze market data and make trading decisions. Always output valid JSON only, no other text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, model: str = "claude-3-opus-20240229"):
        self.client = Anthropic(api_key=settings.anthropic_api_key)
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Anthropic API."""
        try:
            temperature = kwargs.get('temperature', 0.3)
            max_tokens = kwargs.get('max_tokens', 4000)
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system="You are an expert cryptocurrency trader. Analyze market data and make trading decisions. Always output valid JSON only, no other text.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            return message.content[0].text
        
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise


class LocalLLMProvider(BaseLLMProvider):
    """Local LLM provider (Ollama, vLLM, etc.)."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1:70b"):
        self.base_url = base_url
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> str:
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
                    return result['response']
        
        except Exception as e:
            logger.error(f"Local LLM error: {e}")
            raise


class TradingLLM:
    """
    Main LLM interface for trading decisions.
    Supports provider fallback and retry logic.
    """
    
    def __init__(
        self,
        primary_provider: str = "openai",
        model: Optional[str] = None,
        fallback_provider: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.primary = self._get_provider(primary_provider, model, base_url)
        self.fallback = self._get_provider(fallback_provider, model, base_url) if fallback_provider else None
    
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
        Generate trading decision from prompt.
        
        Args:
            prompt: Formatted trading prompt
            max_retries: Number of retries on failure
            **kwargs: Additional parameters for LLM
        
        Returns:
            Parsed JSON response as dict
        """
        for attempt in range(max_retries):
            try:
                # Try primary provider
                response_text = await self.primary.generate(prompt, **kwargs)
                
                # Parse JSON response
                decision = self._parse_response(response_text)
                
                logger.info(f"LLM decision generated successfully (attempt {attempt + 1})")
                return decision
            
            except Exception as e:
                logger.warning(f"Primary provider failed (attempt {attempt + 1}): {e}")
                
                # Try fallback provider
                if self.fallback and attempt == max_retries - 1:
                    try:
                        logger.info("Trying fallback provider...")
                        response_text = await self.fallback.generate(prompt, **kwargs)
                        decision = self._parse_response(response_text)
                        logger.info("Fallback provider succeeded")
                        return decision
                    except Exception as fallback_error:
                        logger.error(f"Fallback provider also failed: {fallback_error}")
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                else:
                    raise
        
        raise RuntimeError("All LLM attempts failed")
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse LLM response to JSON."""
        try:
            # Step 1: Remove reasoning/thinking tags (for reasoning models like o1)
            # These models wrap their reasoning in <think></think> tags
            if "<think>" in response_text and "</think>" in response_text:
                # Remove everything between <think> and </think>
                import re
                response_text = re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL)
                logger.debug("Removed <think></think> tags from response")
            
            # Step 2: Try to extract JSON if wrapped in markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            
            # Step 3: Clean up whitespace
            response_text = response_text.strip()
            
            # Step 4: Parse JSON
            decision = json.loads(response_text)
            
            logger.debug(f"Successfully parsed decision for {len(decision)} coins")
            
            return decision
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text (first 500 chars): {response_text[:500]}...")
            logger.error(f"Response text (last 200 chars): ...{response_text[-200:]}")
            raise ValueError(f"Invalid JSON response from LLM: {e}")

