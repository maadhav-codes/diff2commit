"""OpenAI provider implementation."""

from typing import Dict, Any
from openai import OpenAI
from openai import OpenAIError, AuthenticationError, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from diff2commit.ai_providers.base import AIProvider, CommitMessage
from diff2commit.prompts import SYSTEM_PROMPT, build_commit_prompt


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider for commit message generation."""

    def __init__(self, config: Any):
        """Initialize OpenAI provider.

        Args:
            config: Configuration object

        Raises:
            ValueError: If API key is missing
        """
        super().__init__(config)

        if not config.api_key:
            raise ValueError(
                "OpenAI API key is required. Set AI_COMMIT_API_KEY environment variable."
            )

        self.client = OpenAI(
            api_key=config.api_key, base_url=config.api_endpoint, timeout=config.timeout
        )
        self.model = config.ai_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
    )
    def generate_commit_message(self, diff: str, context: Dict[str, Any]) -> CommitMessage:
        """Generate commit message using OpenAI.

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
            # Call OpenAI API
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
            message_text = response.choices[0].message.content.strip()
            tokens = response.usage.total_tokens if response.usage else 0
            cost = self._calculate_cost(tokens, self.model)

            # Parse message
            return self._parse_message(message_text, tokens, cost)

        except AuthenticationError as e:
            raise ValueError(f"Invalid OpenAI API key: {e}") from e
        except OpenAIError as e:
            raise RuntimeError(f"OpenAI API error: {e}") from e

    def validate_credentials(self) -> bool:
        """Validate OpenAI API credentials.

        Returns:
            True if credentials are valid
        """
        try:
            # Make a minimal API call to test credentials
            self.client.models.list()
            return True
        except AuthenticationError:
            return False
        except OpenAIError:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get OpenAI model information.

        Returns:
            Dictionary with model info
        """
        return {
            "provider": "openai",
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
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
            provider="openai",
            model=self.model,
        )
