"""Configuration management for Expense Intelligence platform.

Loads environment variables from .env file, validates required fields,
and provides a singleton config object.
"""

import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from loguru import logger
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from .env file
load_dotenv()


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    path: str = Field(default="database/expenses.db", description="Path to SQLite database file")
    
    model_config = SettingsConfigDict(env_prefix="DATABASE_")


class GmailConfig(BaseSettings):
    """Gmail API configuration."""

    credentials_path: str = Field(
        default="config/gmail_credentials.json",
        description="Path to Gmail OAuth2 credentials JSON file"
    )
    token_keychain_service: str = Field(
        default="expense-intelligence",
        description="Keychain service name for storing OAuth tokens"
    )
    token_keychain_username: str = Field(
        default="gmail_oauth",
        description="Keychain username for storing OAuth tokens"
    )
    query_label: str = Field(
        default="INBOX",
        description="Gmail label to query for transaction emails"
    )
    sync_interval_minutes: int = Field(
        default=30,
        ge=1,
        description="Interval in minutes between Gmail syncs"
    )
    
    model_config = SettingsConfigDict(env_prefix="GMAIL_")


class FastAPIConfig(BaseSettings):
    """FastAPI server configuration."""

    host: str = Field(default="127.0.0.1", description="FastAPI host")
    port: int = Field(default=8000, ge=1, le=65535, description="FastAPI port")
    reload: bool = Field(default=True, description="Enable auto-reload")
    
    model_config = SettingsConfigDict(env_prefix="FASTAPI_")


class StreamlitConfig(BaseSettings):
    """Streamlit dashboard configuration."""

    host: str = Field(default="127.0.0.1", description="Streamlit host")
    port: int = Field(default=8501, ge=1, le=65535, description="Streamlit port")
    
    model_config = SettingsConfigDict(env_prefix="STREAMLIT_")


class AIConfig(BaseSettings):
    """AI/LLM configuration (optional)."""

    enabled: bool = Field(default=False, description="Enable AI features")
    provider: Literal["openai"] = Field(default="openai", description="AI provider")
    api_key: str = Field(default="", description="API key for AI provider")
    model: str = Field(default="gpt-4o-mini", description="AI model to use")
    max_retries: int = Field(default=3, ge=0, description="Max retries for AI API calls")
    
    model_config = SettingsConfigDict(env_prefix="AI_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    level: Literal["TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Log level"
    )
    path: str = Field(default="logs", description="Directory for log files")
    
    model_config = SettingsConfigDict(env_prefix="LOG_")


class SettingsConfig(BaseSettings):
    """Application settings configuration."""

    local_only: bool = Field(
        default=False,
        description="Run in local-only mode (no AI features)"
    )
    
    model_config = SettingsConfigDict(env_prefix="")


class Config:
    """Main configuration object aggregating all sub-configurations."""
    
    def __init__(self):
        """Initialize and validate all configuration sections."""
        try:
            self.database = DatabaseConfig()
            self.gmail = GmailConfig()
            self.fastapi = FastAPIConfig()
            self.streamlit = StreamlitConfig()
            self.ai = AIConfig()
            self.logging = LoggingConfig()
            self.settings = SettingsConfig()
            
            # Validate critical paths exist or can be created
            self._validate_paths()
            
            # If local_only is set, disable AI
            if self.settings.local_only:
                self.ai.enabled = False
                logger.info("Running in local-only mode, AI features disabled")
            
            logger.info("Configuration loaded and validated successfully")
            
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _validate_paths(self) -> None:
        """Validate that required paths exist or can be created."""
        # Ensure database directory exists
        db_path = Path(self.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure log directory exists
        log_path = Path(self.logging.path)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Check Gmail credentials file exists if Gmail features will be used
        creds_path = Path(self.gmail.credentials_path)
        if not creds_path.exists():
            logger.warning(
                f"Gmail credentials file not found at {creds_path}. "
                "Gmail sync will not work until credentials are configured."
            )
    
    def __repr__(self) -> str:
        """String representation of configuration (sanitized)."""
        return (
            f"Config(\n"
            f"  database.path={self.database.path}\n"
            f"  gmail.credentials_path={self.gmail.credentials_path}\n"
            f"  gmail.sync_interval_minutes={self.gmail.sync_interval_minutes}\n"
            f"  fastapi.host={self.fastapi.host}:{self.fastapi.port}\n"
            f"  streamlit.host={self.streamlit.host}:{self.streamlit.port}\n"
            f"  ai.enabled={self.ai.enabled}\n"
            f"  ai.provider={self.ai.provider}\n"
            f"  logging.level={self.logging.level}\n"
            f"  settings.local_only={self.settings.local_only}\n"
            f")"
        )


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance (singleton pattern)."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """Reset the global configuration instance (useful for testing)."""
    global _config
    _config = None


# Allow running this module directly to test configuration
if __name__ == "__main__":
    config = get_config()
    print(config)
    print("\n✅ Configuration loaded successfully!")
