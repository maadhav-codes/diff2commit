import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from .config import Config
from .errors import ToolError


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Don't forward credentials or source code to a redirected host.
        return None


def generate(config: Config, diff: bytes) -> str:
    key = os.environ.get(config.api_key_env, "").strip()
    local = urlsplit(config.base_url).hostname in ("localhost", "127.0.0.1", "::1")
    if not key and not local:
        raise ToolError(
            f"Missing API key. Set the {config.api_key_env} environment variable."
        )
    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": config.system},
            {
                "role": "user",
                "content": config.user.replace(
                    "{{diff}}", diff.decode("utf-8", errors="replace")
                ),
            },
        ],
    }
    if config.reasoning_effort is not None:
        payload["reasoning_effort"] = config.reasoning_effort
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        config.base_url + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    try:
        opener = urllib.request.build_opener(NoRedirect())
        with opener.open(request, timeout=config.timeout) as response:
            # Bound memory even if a broken endpoint returns an enormous response.
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ToolError("LLM response exceeded 1 MiB.")
        data = json.loads(raw)
        choice = data["choices"][0]
        if choice.get("finish_reason") not in (None, "stop"):
            raise ToolError(
                "LLM did not finish a complete message; try again or use another model."
            )
        message = choice["message"]["content"]
        if not isinstance(message, str) or not message.strip():
            raise ToolError("LLM returned an empty message.")
    except urllib.error.HTTPError as exc:
        hint = {
            401: "Check your API key and endpoint region.",
            403: "Check model access.",
            429: "Rate limit or quota exceeded; try later.",
        }.get(exc.code, "Check your endpoint and model.")
        raise ToolError(f"LLM API returned HTTP {exc.code}. {hint}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ToolError(
            "Cannot reach the LLM API, or the request timed out. Check the endpoint and connection."
        ) from exc
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise ToolError("LLM returned an invalid Chat Completions response.") from exc
    return normalize(message)


def normalize(message: str) -> str:
    message = message.strip()
    lines = message.splitlines()
    if len(lines) >= 3 and lines[0].startswith("```") and lines[-1] == "```":
        message = "\n".join(lines[1:-1]).strip()
    return message


def validate(message: str) -> None:
    if (
        not message
        or any(ord(char) < 32 and char not in "\n\t" for char in message)
        or "\x7f" in message
    ):
        raise ToolError("Commit message is empty or contains control characters.")
    subject = message.splitlines()[0]
    if not re.fullmatch(
        r"(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\([^()\r\n]+\))?!?: \S.*",
        subject,
    ):
        raise ToolError(
            "Use a Conventional Commit subject, for example: feat(cli): add staged diff review"
        )
    if len(subject) > 72:
        raise ToolError("Commit subject exceeds 72 characters. Edit it to be shorter.")
    lines = message.splitlines()
    if len(lines) > 1 and lines[1].strip():
        raise ToolError("Separate the commit subject and body with a blank line.")
