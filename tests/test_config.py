"""Tests for configuration management."""

import pytest
from pytest import MonkeyPatch

from diff2commit.config import Diff2CommitConfig, load_config


def test_config_defaults() -> None:
    """Test default configuration values."""
    config = Diff2CommitConfig(api_key="test-key")

    assert config.ai_provider == "openrouter"
    assert config.ai_model == "qwen/qwen-2.5-coder-32b-instruct:free"
    assert config.max_tokens == 200
    assert config.temperature == 0.7
    assert config.commit_format == "conventional"


def test_config_from_env(monkeypatch: MonkeyPatch) -> None:
    """Test configuration from environment variables."""
    monkeypatch.setenv("D2C_API_KEY", "env-test-key")
    monkeypatch.setenv("D2C_AI_MODEL", "claude-3-sonnet")

    config = load_config()

    assert config.api_key == "env-test-key"
    assert config.ai_model == "claude-3-sonnet"


def test_config_validation() -> None:
    """Test configuration validation."""
    # Valid temperature
    config = Diff2CommitConfig(api_key="test", temperature=0.5)
    assert config.temperature == 0.5

    # Invalid temperature should raise validation error
    with pytest.raises(Exception):
        Diff2CommitConfig(api_key="test", temperature=3.0)
