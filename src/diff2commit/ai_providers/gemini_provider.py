"""Google Gemini provider implementation."""

from typing import Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from diff2commit.ai_providers.base import AIProvider, CommitMessage
from diff2commit.prompts import SYSTEM_PROMPT, build_commit_prompt


class GeminiProvider(AIProvider):
    """Google Gemini provider for commit message generation."""

    def __init__(self, config: Any):
        """Initialize Gemini provider."""
        super().__init__(config)

        if not config.api_key:
            raise ValueError("Gemini API key is required. Set D2C_API_KEY environment variable.")

        self.api_key = config.api_key
        self.model = config.ai_model if "gemini" in config.ai_model else "gemini-pro"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_commit_message(self, diff: str, context: Dict[str, Any]) -> CommitMessage:
        """Generate commit message using Gemini."""
        prompt = build_commit_prompt(
            diff=diff,
            files_changed=context.get("files_changed", []),
            additions=context.get("additions", 0),
            deletions=context.get("deletions", 0),
            change_types=context.get("change_types", {}),
            include_emoji=self.config.include_emoji,
        )

        full_prompt = f"{SYSTEM_PROMPT}\\n\\n{prompt}"

        try:
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

            response = requests.post(
                url,
                json={
                    "contents": [{"parts": [{"text": full_prompt}]}],
                    "generationConfig": {
                        "temperature": self.config.temperature,
                        "maxOutputTokens": self.config.max_tokens,
                    },
                },
                timeout=self.config.timeout,
            )
            response.raise_for_status()

            data = response.json()
            message_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

            # Estimate tokens (Gemini doesn't always return this)
            tokens = len(message_text.split()) + len(diff.split())
            cost = self._calculate_cost(tokens, self.model)

            return self._parse_message(message_text, tokens, cost)

        except Exception as e:
            raise RuntimeError(f"Gemini API error: {e}") from e

    def validate_credentials(self) -> bool:
        """Validate Gemini API credentials."""
        try:
            url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
            response = requests.post(
                url, json={"contents": [{"parts": [{"text": "test"}]}]}, timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "provider": "gemini",
            "model": self.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

    def _parse_message(self, text: str, tokens: int, cost: float) -> CommitMessage:
        """Parse generated message."""
        lines = text.strip().split("\\n")
        subject = lines[0].strip() if lines else ""

        body_lines = [line for line in lines[1:] if line.strip()]

        max_len = self.config.max_subject_length
        if len(subject) > max_len:
            subject = subject[: max_len - 3] + "..."

        return CommitMessage(
            subject=subject,
            body="\\n".join(body_lines).strip() if body_lines else None,
            raw=text,
            tokens_used=tokens,
            cost=cost,
            provider="gemini",
            model=self.model,
        )
