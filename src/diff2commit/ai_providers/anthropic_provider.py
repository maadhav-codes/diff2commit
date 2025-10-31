"""Anthropic Claude provider implementation."""

from typing import Dict, Any
from anthropic import Anthropic, AuthenticationError, RateLimitError
from anthropic.types import TextBlock
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from diff2commit.ai_providers.base import AIProvider, CommitMessage
from diff2commit.prompts import SYSTEM_PROMPT, build_commit_prompt


class AnthropicProvider(AIProvider):
    """Anthropic Claude provider for commit message generation."""

    def __init__(self, config: Any):
        """Initialize Anthropic provider."""
        super().__init__(config)

        if not config.api_key:
            raise ValueError("Anthropic API key is required. Set D2C_API_KEY environment variable.")

        self.client = Anthropic(api_key=config.api_key, timeout=config.timeout)
        self.model = config.ai_model if "claude" in config.ai_model else "claude-3-sonnet-20240229"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def generate_commit_message(self, diff: str, context: Dict[str, Any]) -> CommitMessage:
        """Generate commit message using Anthropic Claude."""
        prompt = build_commit_prompt(
            diff=diff,
            files_changed=context.get("files_changed", []),
            additions=context.get("additions", 0),
            deletions=context.get("deletions", 0),
            change_types=context.get("change_types", {}),
            include_emoji=self.config.include_emoji,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Type narrow to TextBlock before accessing .text
            content_block = response.content[0]
            if isinstance(content_block, TextBlock):
                message_text = content_block.text.strip()
            else:
                raise RuntimeError(f"Unexpected content block type: {type(content_block)}")

            tokens = response.usage.input_tokens + response.usage.output_tokens
            cost = self._calculate_cost(tokens, self.model)

            return self._parse_message(message_text, tokens, cost)

        except AuthenticationError as e:
            raise ValueError(f"Invalid Anthropic API key: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Anthropic API error: {e}") from e

    def validate_credentials(self) -> bool:
        """Validate Anthropic API credentials."""
        try:
            # Test with minimal request
            self.client.messages.create(
                model=self.model, max_tokens=10, messages=[{"role": "user", "content": "test"}]
            )
            return True
        except (AuthenticationError, RateLimitError):
            return False
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "provider": "anthropic",
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

    def _parse_message(self, text: str, tokens: int, cost: float) -> CommitMessage:
        """Parse generated message."""
        lines = text.strip().split("\\n")
        subject = lines[0].strip() if lines else ""

        body_lines = []
        for line in lines[1:]:
            if line.strip():
                body_lines.append(line)

        max_len = self.config.max_subject_length
        if len(subject) > max_len:
            subject = subject[: max_len - 3] + "..."

        return CommitMessage(
            subject=subject,
            body="\\n".join(body_lines).strip() if body_lines else None,
            raw=text,
            tokens_used=tokens,
            cost=cost,
            provider="anthropic",
            model=self.model,
        )
