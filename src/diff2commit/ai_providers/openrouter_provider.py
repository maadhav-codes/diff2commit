"""OpenRouter provider implementation."""

from typing import Any, Dict

from openai import AuthenticationError, OpenAI, OpenAIError, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from diff2commit.ai_providers.base import AIProvider, CommitMessage
from diff2commit.prompts import SYSTEM_PROMPT, build_commit_prompt


class OpenRouterProvider(AIProvider):
    """OpenRouter provider for commit message generation"""

    # Default free API key provided by the CLI
    DEFAULT_FREE_API_KEY = (
        "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"
    )

    def __init__(self, config: Any):
        """Initialize OpenRouter provider.

        Args:
            config: Configuration object
        """
        super().__init__(config)

        # Use default free API key if none provided
        api_key = config.api_key or self.DEFAULT_FREE_API_KEY

        # OpenRouter uses OpenAI-compatible API
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            timeout=config.timeout,
            default_headers={
                "HTTP-Referer": "https://github.com/maadhav-codes/diff2commit",
                "X-Title": "diff2commit",
            },
        )

        # Use Qwen free model by default
        self.model = config.ai_model
        self.is_free_tier = "free" in self.model.lower()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def generate_commit_message(self, diff: str, context: Dict[str, Any]) -> CommitMessage:
        """Generate commit message using OpenRouter.

        Args:
            diff: Git diff text
            context: Additional context

        Returns:
            CommitMessage object
        """
        # Build prompt
        prompt = build_commit_prompt(
            diff=diff,
            files_changed=context.get("files_changed", []),
            additions=context.get("additions", 0),
            deletions=context.get("deletions", 0),
            change_types=context.get("change_types", {}),
            include_emoji=self.config.include_emoji,
        )

        try:
            # Call OpenRouter API (OpenAI-compatible)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )

            # Extract message
            message_content = response.choices[0].message.content
            if message_content is None:
                raise ValueError("OpenRouter API returned empty response")
            message_text = message_content.strip()

            tokens = response.usage.total_tokens if response.usage else 0

            # Free tier has no cost
            cost = 0.0 if self.is_free_tier else self._calculate_cost(tokens, self.model)

            # Parse message
            return self._parse_message(message_text, tokens, cost)

        except AuthenticationError as e:
            raise ValueError(f"Invalid OpenRouter API key: {e}") from e
        except OpenAIError as e:
            raise RuntimeError(f"OpenRouter API error: {e}") from e

    def validate_credentials(self) -> bool:
        """Validate OpenRouter API credentials.

        Returns:
            True if credentials are valid
        """
        try:
            # Make a minimal API call to test credentials
            self.client.chat.completions.create(
                model=self.model, messages=[{"role": "user", "content": "test"}], max_tokens=5
            )
            return True
        except AuthenticationError:
            return False
        except OpenAIError:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenRouter model information.

        Returns:
            Dictionary with model info
        """
        return {
            "provider": "openrouter",
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "free_tier": self.is_free_tier,
            "cost": "Free" if self.is_free_tier else "Paid",
        }

    def _parse_message(self, text: str, tokens: int, cost: float) -> CommitMessage:
        """Parse the generated message text.

        Args:
            text: Generated message text
            tokens: Token count
            cost: Estimated cost

        Returns:
            CommitMessage object
        """
        lines = text.strip().split("\\n")

        # Extract subject (first non-empty line)
        subject = ""
        body_lines = []
        footer_lines = []

        in_body = False
        in_footer = False

        for line in lines:
            if not subject and line.strip():
                subject = line.strip()
            elif not in_footer and line.strip().startswith(
                ("BREAKING CHANGE:", "Refs:", "Closes:")
            ):
                in_footer = True
                footer_lines.append(line.strip())
            elif in_footer:
                footer_lines.append(line.strip())
            elif line.strip() or in_body:
                in_body = True
                body_lines.append(line)

        # Truncate subject if too long
        max_len = self.config.max_subject_length
        if len(subject) > max_len:
            subject = subject[: max_len - 3] + "..."

        return CommitMessage(
            subject=subject,
            body="\\n".join(body_lines).strip() if body_lines else None,
            footer="\\n".join(footer_lines).strip() if footer_lines else None,
            raw=text,
            tokens_used=tokens,
            cost=cost,
            provider="openrouter",
            model=self.model,
        )
