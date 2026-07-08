"""Unit tests for configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.config import Config, get_config, reset_config


class TestConfig:
    """Test suite for Config class."""
    
    def setup_method(self):
        """Reset config before each test."""
        reset_config()
    
    def teardown_method(self):
        """Reset config after each test."""
        reset_config()
    
    def test_config_loads_with_defaults(self):
        """Test that config loads with default values when env vars are not set."""
        # Remove env vars that might override defaults
        env_vars_to_remove = [
            "DATABASE_PATH",
            "GMAIL_CREDENTIALS_PATH",
            "AI_ENABLED",
            "LOCAL_ONLY",
        ]
        
        original_env = {k: os.environ.get(k) for k in env_vars_to_remove}
        for var in env_vars_to_remove:
            os.environ.pop(var, None)
        
        try:
            reset_config()
            config = get_config()
            
            assert config.database.path == "database/expenses.db"
            assert config.gmail.credentials_path == "config/gmail_credentials.json"
            assert config.gmail.sync_interval_minutes == 30
            assert config.fastapi.host == "127.0.0.1"
            assert config.fastapi.port == 8000
            assert config.streamlit.host == "127.0.0.1"
            assert config.streamlit.port == 8501
            assert config.ai.enabled is False
            assert config.ai.provider == "openai"
            assert config.logging.level == "INFO"
            assert config.settings.local_only is False
        finally:
            # Restore original env vars
            for var, value in original_env.items():
                if value is not None:
                    os.environ[var] = value
    
    def test_config_loads_from_env(self):
        """Test that config loads values from environment variables."""
        env_vars = {
            "DATABASE_PATH": "custom/path/db.sqlite",
            "GMAIL_SYNC_INTERVAL_MINUTES": "60",
            "FASTAPI_PORT": "9000",
            "AI_ENABLED": "true",
            "LOG_LEVEL": "DEBUG",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            reset_config()
            config = get_config()
            
            assert config.database.path == "custom/path/db.sqlite"
            assert config.gmail.sync_interval_minutes == 60
            assert config.fastapi.port == 9000
            assert config.ai.enabled is True
            assert config.logging.level == "DEBUG"
    
    def test_config_creates_directories(self):
        """Test that config creates required directories."""
        with patch.dict(os.environ, {"DATABASE_PATH": "test_dir/test.db"}, clear=False):
            reset_config()
            config = get_config()
            
            # Check that database directory was created
            db_path = Path(config.database.path)
            assert db_path.parent.exists()
            
            # Clean up
            if db_path.parent.exists():
                db_path.parent.rmdir()
    
    def test_local_only_disables_ai(self):
        """Test that setting local_only disables AI features."""
        env_vars = {
            "AI_ENABLED": "true",
            "LOCAL_ONLY": "true",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            reset_config()
            config = get_config()
            
            # Even though AI_ENABLED is true, local_only should override
            assert config.ai.enabled is False
    
    def test_config_singleton(self):
        """Test that get_config returns the same instance (singleton pattern)."""
        config1 = get_config()
        config2 = get_config()
        
        assert config1 is config2
    
    def test_reset_config(self):
        """Test that reset_config clears the singleton instance."""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        
        assert config1 is not config2
    
    def test_invalid_sync_interval_raises_error(self):
        """Test that invalid sync interval raises validation error."""
        env_vars = {
            "GMAIL_SYNC_INTERVAL_MINUTES": "0",  # Must be >= 1
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            reset_config()
            with pytest.raises(Exception):  # Pydantic ValidationError
                get_config()
    
    def test_invalid_fastapi_port_raises_error(self):
        """Test that invalid FastAPI port raises validation error."""
        env_vars = {
            "FASTAPI_PORT": "70000",  # Must be <= 65535
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            reset_config()
            with pytest.raises(Exception):  # Pydantic ValidationError
                get_config()
    
    def test_invalid_log_level_raises_error(self):
        """Test that invalid log level raises validation error."""
        env_vars = {
            "LOG_LEVEL": "INVALID_LEVEL",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            reset_config()
            with pytest.raises(Exception):  # Pydantic ValidationError
                get_config()
    
    def test_config_repr(self):
        """Test that config repr returns expected string."""
        config = get_config()
        repr_str = repr(config)
        
        assert "Config(" in repr_str
        assert "database.path=" in repr_str
        assert "fastapi.host=" in repr_str
        assert "ai.enabled=" in repr_str
