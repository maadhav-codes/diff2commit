import math
import os
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from .errors import ToolError

REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")


@dataclass(frozen=True)
class Config:
    base_url: str
    model: str
    api_key_env: str
    timeout: float
    max_diff_bytes: int
    system: str
    user: str
    reasoning_effort: str | None = None


def default_yaml() -> str:
    return files("diff2commit").joinpath("default.yaml").read_text(encoding="utf-8")


def load_config(path: Path | None, overrides: dict) -> Config:
    data = yaml.safe_load(default_yaml())
    if path is not None:
        try:
            custom = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ToolError(f"Cannot read YAML configuration: {path}") from exc
        if not isinstance(custom, dict) or set(custom) - set(data):
            raise ToolError(
                "Configuration must be a mapping with llm, prompt, or max_diff_bytes."
            )
        for key, value in custom.items():
            if key in ("llm", "prompt"):
                if not isinstance(value, dict) or set(value) - set(data[key]):
                    raise ToolError(f"Invalid or unknown keys in {key} configuration.")
                data[key].update(value)
            else:
                data[key] = value

    llm = data["llm"]
    for key in ("base_url", "model", "api_key_env", "timeout", "reasoning_effort"):
        env_value = os.environ.get(f"DIFF2COMMIT_{key.upper()}")
        if env_value is not None:
            llm[key] = env_value
        if overrides.get(key) is not None:
            llm[key] = overrides[key]
    for key in ("base_url", "model", "api_key_env"):
        if not isinstance(llm[key], str) or not llm[key].strip():
            raise ToolError(
                f"Set llm.{key} in YAML, DIFF2COMMIT_{key.upper()}, or --{key.replace('_', '-')}."
            )
        llm[key] = llm[key].strip()
    try:
        url = urlsplit(llm["base_url"])
        valid_url = url.hostname and url.port != 0
    except ValueError as exc:
        raise ToolError("Invalid llm.base_url.") from exc
    if not valid_url or url.username or url.password or url.query or url.fragment:
        raise ToolError(
            "base_url must be a plain API URL without credentials, query, or fragment."
        )
    if url.scheme != "https" and not (
        url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ToolError(
            "Use HTTPS for remote endpoints; HTTP is allowed only on loopback."
        )
    try:
        timeout = float(llm["timeout"])
    except (ValueError, TypeError) as exc:
        raise ToolError("llm.timeout must be a positive number.") from exc
    if isinstance(llm["timeout"], bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ToolError("llm.timeout must be a positive finite number.")
    limit = data["max_diff_bytes"]
    if type(limit) is not int or limit <= 0:
        raise ToolError("max_diff_bytes must be a positive integer.")
    prompt = data["prompt"]
    if any(
        not isinstance(prompt[k], str) or not prompt[k].strip()
        for k in ("system", "user")
    ):
        raise ToolError("prompt.system and prompt.user must be nonempty strings.")
    if prompt["user"].count("{{diff}}") != 1:
        raise ToolError("prompt.user must contain exactly one {{diff}} placeholder.")
    effort = llm["reasoning_effort"]
    if effort is not None and (
        not isinstance(effort, str) or effort not in REASONING_EFFORTS
    ):
        raise ToolError(
            "llm.reasoning_effort must be null or one of: "
            + ", ".join(REASONING_EFFORTS)
        )
    return Config(
        llm["base_url"].rstrip("/"),
        llm["model"],
        llm["api_key_env"],
        timeout,
        limit,
        prompt["system"],
        prompt["user"],
        effort,
    )
