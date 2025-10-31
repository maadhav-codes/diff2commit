"""Base abstract class for AI providers."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CommitMessage:
    """Represents a generated commit message."""

    subject: str
    body: Optional[str] = None
    footer: Optional[str] = None
    raw: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    provider: str = ""
    model: str = ""

    def format(self) -> str:
        """Format the commit message."""
        parts = [self.subject]

        if self.body:
            parts.append("")  # Blank line
            parts.append(self.body)

        if self.footer:
            parts.append("")  # Blank line
            parts.append(self.footer)

        return "\\n".join(parts)

    def validate_conventional(self) -> bool:
        """Validate if message follows Conventional Commits format."""
        conventional_types = [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "build",
            "ci",
            "chore",
            "revert",
        ]

        # Check if subject starts with a valid type
        for commit_type in conventional_types:
            if self.subject.startswith(f"{commit_type}:") or self.subject.startswith(
                f"{commit_type}("
            ):
                return True

        return False


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, config: Any):
        """Initialize the provider.

        Args:
            config: Configuration object
        """
        self.config = config

    @abstractmethod
    def generate_commit_message(self, diff: str, context: Dict[str, Any]) -> CommitMessage:
        """Generate a commit message from a diff.

        Args:
            diff: Git diff text
            context: Additional context (files, stats, etc.)

        Returns:
            CommitMessage object

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate API credentials.

        Returns:
            True if credentials are valid

        Raises:
            Exception: If validation fails
        """
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.

        Returns:
            Dictionary with model information
        """
        pass

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate cost based on token usage.

        Args:
            tokens: Number of tokens used
            model: Model name

        Returns:
            Estimated cost in USD
        """
        # Pricing per 1K tokens (approximate as of 2025)
        pricing = {
            # OpenAI
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            # Anthropic
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            # Gemini
            "gemini-pro": {"input": 0.00025, "output": 0.0005},
            "gemini-ultra": {"input": 0.001, "output": 0.002},
        }

        # Find matching pricing
        for model_name, prices in pricing.items():
            if model_name in model.lower():
                # Estimate input/output split (rough 70/30)
                input_tokens = int(tokens * 0.7)
                output_tokens = int(tokens * 0.3)
                return (
                    input_tokens * prices["input"] / 1000 + output_tokens * prices["output"] / 1000
                )

        # Default estimate
        return tokens * 0.002 / 1000
