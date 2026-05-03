"""
Configuration management for PR Guardian
Loads configuration from YAML file and environment variables
"""

from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class GitHubConfig(BaseModel):
    """GitHub configuration"""
    token: Optional[str] = Field(default=None, description="GitHub API token")
    api_url: str = Field(default="https://api.github.com", description="GitHub API URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class AIConfig(BaseModel):
    """AI/LLM configuration"""
    provider: str = Field(default="watsonx", description="AI provider (watsonx/openai/anthropic)")
    model: Optional[str] = Field(default=None, description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    url: Optional[str] = Field(default=None, description="API URL")
    temperature: float = Field(default=0.3, description="Temperature for generation")
    max_tokens: int = Field(default=2000, description="Maximum tokens to generate")


class AppConfig(BaseModel):
    """Application configuration"""
    log_level: str = Field(default="INFO", description="Logging level")
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")


class Config(BaseSettings):
    """Main configuration class"""
    
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    
    class Config:
        env_prefix = "PR_GUARDIAN_"
        env_nested_delimiter = "__"
        case_sensitive = False


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file and environment variables
    
    Priority (highest to lowest):
    1. Environment variables (PR_GUARDIAN_*)
    2. Config file specified in config_path
    3. ~/.pr-guardian/config.yaml
    4. Default values
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Config object with loaded settings
    """
    config_data: Dict[str, Any] = {}
    
    # Determine config file path
    if config_path:
        yaml_path = Path(config_path)
    else:
        yaml_path = Path.home() / ".pr-guardian" / "config.yaml"
    
    # Load from YAML if exists
    if yaml_path.exists():
        try:
            with open(yaml_path, 'r') as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data:
                    config_data = yaml_data
        except Exception as e:
            print(f"Warning: Failed to load config from {yaml_path}: {e}")
    
    # Override with environment variables
    env_overrides = _load_from_env()
    config_data = _deep_merge(config_data, env_overrides)
    
    # Create Config object
    return Config(**config_data)


def _load_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables"""
    config: Dict[str, Any] = {
        "github": {},
        "ai": {},
        "app": {}
    }
    
    # GitHub configuration
    if token := os.getenv("GITHUB_TOKEN"):
        config["github"]["token"] = token
    if api_url := os.getenv("GITHUB_API_URL"):
        config["github"]["api_url"] = api_url
    
    # AI configuration
    if provider := os.getenv("AI_PROVIDER"):
        config["ai"]["provider"] = provider
    if model := os.getenv("AI_MODEL"):
        config["ai"]["model"] = model
    if api_key := os.getenv("AI_API_KEY"):
        config["ai"]["api_key"] = api_key
    if url := os.getenv("AI_URL"):
        config["ai"]["url"] = url
    
    # Watsonx specific
    if watsonx_key := os.getenv("WATSONX_API_KEY"):
        config["ai"]["api_key"] = watsonx_key
    if watsonx_url := os.getenv("WATSONX_URL"):
        config["ai"]["url"] = watsonx_url
    
    # OpenAI specific
    if openai_key := os.getenv("OPENAI_API_KEY"):
        config["ai"]["api_key"] = openai_key
    
    # Anthropic specific
    if anthropic_key := os.getenv("ANTHROPIC_API_KEY"):
        config["ai"]["api_key"] = anthropic_key
    
    # App configuration
    if log_level := os.getenv("LOG_LEVEL"):
        config["app"]["log_level"] = log_level
    
    return config


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries"""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def save_config(config: Config, config_path: Optional[str] = None) -> None:
    """
    Save configuration to YAML file
    
    Args:
        config: Config object to save
        config_path: Optional path to save config file
    """
    if config_path:
        yaml_path = Path(config_path)
    else:
        yaml_path = Path.home() / ".pr-guardian" / "config.yaml"
    
    # Create directory if it doesn't exist
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict and save
    config_dict = config.model_dump(exclude_none=True)
    
    with open(yaml_path, 'w') as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)

# Made with Bob
