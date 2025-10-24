"""Configuration management for the trading system."""

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    enable_paper_trading: bool = Field(default=True, env="ENABLE_PAPER_TRADING")
    use_testnet: bool = Field(default=False, env="USE_TESTNET")  # 使用币安testnet模拟平台
    
    # Exchange
    binance_api_key: str = Field(default="", env="BINANCE_API_KEY")
    binance_api_secret: str = Field(default="", env="BINANCE_API_SECRET")
    
    # AI Providers
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_base_url: Optional[str] = Field(default=None, env="OPENAI_BASE_URL")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    
    # Database
    database_url: str = Field(
        default="postgresql://trading_user:password@localhost:5432/trading_db",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Telegram
    telegram_bot_token: str = Field(default="", env="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", env="TELEGRAM_CHAT_ID")
    
    # Optional Enhanced Data
    glassnode_api_key: str = Field(default="", env="GLASSNODE_API_KEY")
    cryptopanic_api_key: str = Field(default="", env="CRYPTOPANIC_API_KEY")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class TradingConfig:
    """Trading configuration loaded from YAML files."""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.trading_config = self._load_yaml("trading_config.yaml")
        self.risk_params = self._load_yaml("risk_params.yaml")
    
    def _load_yaml(self, filename: str) -> Dict:
        """Load YAML configuration file."""
        filepath = self.config_dir / filename
        with open(filepath, 'r') as f:
            return yaml.safe_load(f)
    
    @property
    def exchange_name(self) -> str:
        return self.trading_config['exchange']['name']
    
    @property
    def trading_pairs(self) -> List[str]:
        return self.trading_config['trading_pairs']
    
    @property
    def decision_interval_minutes(self) -> float:
        return self.trading_config['ai']['decision_interval_minutes']
    
    @property
    def ai_provider(self) -> str:
        return self.trading_config['ai']['provider']
    
    @property
    def ai_model(self) -> str:
        return self.trading_config['ai']['model']
    
    @property
    def ai_base_url(self) -> Optional[str]:
        """Get AI base URL from config (can be overridden by env var)."""
        base_url = self.trading_config['ai'].get('base_url', '')
        return base_url if base_url else None
    
    @property
    def is_reasoning_model(self) -> bool:
        """Check if the AI model is a reasoning model (e.g., DeepSeek-R1, o1)."""
        return self.trading_config['ai'].get('is_reasoning_model', False)
    
    def get_ai_generation_kwargs(self) -> Dict:
        """
        Get optional LLM generation parameters from config.
        
        Returns dict with optional keys like:
            - temperature, max_tokens, stream
            - thinking_budget, response_format, extra_body
        """
        ai_config = self.trading_config['ai']
        kwargs = {}
        
        # Standard parameters
        if 'temperature' in ai_config:
            kwargs['temperature'] = ai_config['temperature']
        if 'max_tokens' in ai_config:
            kwargs['max_tokens'] = ai_config['max_tokens']
        
        # Optional reasoning/streaming parameters
        if 'stream' in ai_config:
            kwargs['stream'] = ai_config['stream']
        if 'thinking_budget' in ai_config:
            kwargs['thinking_budget'] = ai_config['thinking_budget']
        if 'response_format' in ai_config:
            kwargs['response_format'] = ai_config['response_format']
        if 'extra_body' in ai_config:
            kwargs['extra_body'] = ai_config['extra_body']
        
        return kwargs
    
    @property
    def max_risk_per_trade(self) -> float:
        return self.risk_params['position_sizing']['max_risk_per_trade_percent']
    
    @property
    def leverage_config(self) -> Dict:
        return self.risk_params['leverage']
    
    @property
    def max_daily_drawdown(self) -> float:
        return self.risk_params['drawdown_protection']['max_daily_drawdown_percent']
    
    def get_leverage_for_confidence(self, confidence: float) -> int:
        """Get appropriate leverage based on AI confidence score."""
        mapping = self.risk_params['leverage']['confidence_mapping']
        
        for conf_threshold in sorted(mapping.keys(), reverse=True):
            if confidence >= conf_threshold:
                return mapping[conf_threshold]
        
        return self.risk_params['leverage']['default']


# Global instances
settings = Settings()
trading_config = TradingConfig()


class UnifiedConfig:
    """Unified configuration interface combining Settings and TradingConfig."""
    
    def __init__(self, base_settings: Settings, trading_cfg: TradingConfig):
        self._settings = base_settings
        self._trading_cfg = trading_cfg
    
    # Environment settings
    @property
    def environment(self) -> str:
        return self._settings.environment
    
    @property
    def paper_trading(self) -> bool:
        return self._settings.enable_paper_trading
    
    # Exchange settings
    @property
    def exchange(self) -> str:
        return self._trading_cfg.exchange_name
    
    @property
    def exchange_api_key(self) -> str:
        return self._settings.binance_api_key
    
    @property
    def exchange_api_secret(self) -> str:
        return self._settings.binance_api_secret
    
    # Trading settings
    @property
    def trading_pairs(self) -> List[str]:
        return self._trading_cfg.trading_pairs
    
    @property
    def decision_interval_minutes(self) -> float:
        return self._trading_cfg.decision_interval_minutes
    
    # AI settings
    @property
    def ai_provider(self) -> str:
        return self._trading_cfg.ai_provider
    
    @property
    def ai_model(self) -> str:
        return self._trading_cfg.ai_model
    
    @property
    def openai_api_key(self) -> str:
        return self._settings.openai_api_key
    
    @property
    def openai_base_url(self) -> Optional[str]:
        # Environment variable takes precedence
        return self._settings.openai_base_url or self._trading_cfg.ai_base_url
    
    @property
    def anthropic_api_key(self) -> str:
        return self._settings.anthropic_api_key
    
    # Risk settings
    @property
    def max_risk_per_trade(self) -> float:
        return self._trading_cfg.max_risk_per_trade
    
    @property
    def max_daily_drawdown(self) -> float:
        return self._trading_cfg.max_daily_drawdown
    
    # Database
    @property
    def database_url(self) -> str:
        return self._settings.database_url
    
    # Redis
    @property
    def redis_url(self) -> str:
        return self._settings.redis_url
    
    # Telegram
    @property
    def telegram_bot_token(self) -> str:
        return self._settings.telegram_bot_token
    
    @property
    def telegram_chat_id(self) -> str:
        return self._settings.telegram_chat_id
    
    def get_leverage_for_confidence(self, confidence: float) -> int:
        return self._trading_cfg.get_leverage_for_confidence(confidence)


# Unified config instance (recommended for use)
config = UnifiedConfig(settings, trading_config)

