"""Configuration management for Diff2Commit CLI."""

from typing import Optional, Literal
from pathlib import Path

from pydantic import Field, field_validator, ValidationInfo
from pydantic_settings import BaseSettings, SettingsConfigDict


class Diff2CommitConfig(BaseSettings):
    """Configuration for Diff2Commit CLI tool."""

    # AI Provider Settings
    ai_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        description="AI provider to use for generating commit messages",
    )
    ai_model: str = Field(default="gpt-4", description="AI model to use")
    api_key: Optional[str] = Field(default=None, description="API key for the AI provider")
    api_endpoint: Optional[str] = Field(default=None, description="Custom API endpoint (optional)")

    # Generation Settings
    max_tokens: int = Field(
        default=200, ge=50, le=1000, description="Maximum tokens for generation"
    )
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    timeout: int = Field(default=30, ge=5, le=120, description="API request timeout in seconds")
    max_retries: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")

    # Commit Message Settings
    commit_format: Literal["conventional", "custom"] = Field(
        default="conventional", description="Commit message format"
    )
    include_emoji: bool = Field(default=False, description="Include emojis in commit messages")
    max_subject_length: int = Field(
        default=72, ge=50, le=100, description="Maximum length for commit subject"
    )

    # Cost Tracking
    track_usage: bool = Field(default=True, description="Track token usage and costs")
    cost_limit_monthly: Optional[float] = Field(
        default=None, description="Monthly cost limit in USD"
    )

    # Advanced Settings
    verbose: bool = Field(default=False, description="Enable verbose output")

    model_config = SettingsConfigDict(
        env_prefix="D2C_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate API key based on provider."""
        # API key validation happens at runtime when provider is initialized
        return v

    def get_config_path(self) -> Path:
        """Get the configuration file path."""
        home = Path.home()
        config_dir = home / ".config" / "d2c"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.toml"

    def get_usage_db_path(self) -> Path:
        """Get the usage database path."""
        home = Path.home()
        data_dir = home / ".local" / "share" / "d2c"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "usage.db"


def load_config() -> Diff2CommitConfig:
    """Load configuration from environment and files."""
    return Diff2CommitConfig()
