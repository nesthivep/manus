import os
import threading
import tomllib
from pathlib import Path
from typing import Dict, Optional

from pydantic import BaseModel, Field, validator
from .exceptions import ConfigError


def get_project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = get_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class LLMSettings(BaseModel):
    model: str = Field(..., description="Model name")
    base_url: str = Field(..., description="API base URL")
    api_key: str = Field(..., description="API key")
    max_tokens: int = Field(4096, description="Maximum number of tokens per request")
    temperature: float = Field(1.0, description="Sampling temperature")
    api_type: str = Field(..., description="AzureOpenai or Openai")
    api_version: str = Field(..., description="Azure Openai version if AzureOpenai")

    @validator('api_type')
    def validate_api_type(cls, v):
        if v not in ['AzureOpenai', 'Openai']:
            raise ConfigError(f"Invalid api_type: {v}. Must be 'AzureOpenai' or 'Openai'")
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if not 0.0 <= v <= 2.0:
            raise ConfigError(f"Temperature must be between 0.0 and 2.0, got {v}")
        return v


class AppConfig(BaseModel):
    llm: Dict[str, LLMSettings]


class Config:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = None
                    self._load_initial_config()
                    self._initialized = True

    @staticmethod
    def _get_config_path() -> Path:
        # 首先检查环境变量中的配置路径
        env_config_path = os.getenv('OPENMANUS_CONFIG_PATH')
        if env_config_path:
            config_path = Path(env_config_path)
            if config_path.exists():
                return config_path

        root = PROJECT_ROOT
        config_path = root / "config" / "config.toml"
        if config_path.exists():
            return config_path
        example_path = root / "config" / "config.example.toml"
        if example_path.exists():
            return example_path
        raise ConfigError("No configuration file found in config directory")

    def _load_config(self) -> dict:
        config_path = self._get_config_path()
        try:
            with config_path.open("rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise ConfigError(f"Error loading config file: {str(e)}")

    def _load_initial_config(self):
        raw_config = self._load_config()
        base_llm = raw_config.get("llm", {})
        
        # 从环境变量获取API密钥
        api_key = os.getenv('OPENMANUS_API_KEY') or base_llm.get("api_key")
        if not api_key:
            raise ConfigError("API key not found in config or environment variables")

        llm_overrides = {
            k: v for k, v in raw_config.get("llm", {}).items() if isinstance(v, dict)
        }

        default_settings = {
            "model": base_llm.get("model"),
            "base_url": base_llm.get("base_url"),
            "api_key": api_key,
            "max_tokens": base_llm.get("max_tokens", 4096),
            "temperature": base_llm.get("temperature", 1.0),
            "api_type": base_llm.get("api_type", ""),
            "api_version": base_llm.get("api_version", ""),
        }

        try:
            config_dict = {
                "llm": {
                    "default": default_settings,
                    **{
                        name: {**default_settings, **override_config}
                        for name, override_config in llm_overrides.items()
                    },
                }
            }
            self._config = AppConfig(**config_dict)
        except Exception as e:
            raise ConfigError(f"Error validating config: {str(e)}")

    @property
    def llm(self) -> Dict[str, LLMSettings]:
        return self._config.llm


config = Config()
