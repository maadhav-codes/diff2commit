# diff2commit

Generate and review Conventional Commit messages from staged Git changes using an
LLM. The CLI shows your staged files and diff, generates a message, and lets you
accept, edit, regenerate, or cancel before committing.

The default configuration targets a local Ollama model. You can also configure an
OpenAI-compatible Chat Completions endpoint.

## Requirements

- Python 3.10 or newer
- Git on your `PATH`
- A running LLM endpoint and an available model
- An API key when using a remote endpoint

## Installation

From this checkout, install into a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Alternatively, if you use `uv`, the repository includes a lockfile:

```sh
uv sync
uv run diff2commit --help
```

The examples below assume the `diff2commit` command is on your `PATH`. You can
also use `python -m diff2commit`, or prefix commands with `uv run`.

## Quick start with Ollama

With Ollama installed and its server running, create the model configured by this
repository. Run these commands from this checkout:

```sh
ollama pull qwen2.5-coder:7b
ollama create diff2commit-qwen:7b -f configs/Modelfile
```

The Modelfile uses Qwen2.5-Coder 7B with a 16,384-token context and temperature
`0.2`. The CLI defaults to `http://localhost:11434/v1`, model
`diff2commit-qwen:7b`, and a 180-second request timeout. A key is optional for
loopback endpoints.

In the Git repository you want to commit:

```sh
# Optional: create an editable starter configuration in this directory.
diff2commit --init

# Stage the changes you want included, then review a generated message.
git add path/to/file
diff2commit
```

Run `--init` from the repository root for automatic configuration discovery. It
creates `.diff2commit.yaml` in the current directory and refuses to overwrite an
existing file. Without a configuration file, the bundled defaults still apply.

Preview the terminal interface without Git or model requests:

```sh
diff2commit --demo
```

## Reviewing and committing

Interactive review requires a terminal. Choose an action and press Enter:

| Action | Behavior |
| --- | --- |
| `a` / `accept` | Commit with the displayed message if it passes validation. |
| `e` / `edit` | Open the message in your editor, then validate it again. |
| `r` / `regenerate` | Request another message using the same staged diff. |
| `d` / `diff` | Show the full staged diff. |
| `q` / `quit` / Enter | Cancel without committing. |

Editor selection follows `VISUAL`, then `EDITOR`, then Git's `GIT_EDITOR` value.
Editor arguments are supported, for example `export EDITOR='code --wait'`.

For noninteractive use:

```sh
# Generate and print a valid message without creating a commit.
diff2commit --dry-run

# Generate, validate, and commit immediately without interactive review.
diff2commit --yes

# Save the exact staged diff to a new file before generation.
diff2commit --dry-run --save-diff /tmp/staged-changes.diff
```

`--dry-run` still calls the configured LLM. `--save-diff` refuses to overwrite a
file and creates it with permissions `0600`. Generation failures can leave that
saved file in place.

Rich panels, colors, and animations are enabled in a supported terminal. Use
`--plain` to disable them; redirected output also uses plain presentation. In
dry-run mode the message goes to stdout and endpoint information goes to stderr.

## Configuration

The CLI automatically loads `.diff2commit.yaml` from the Git repository root, or
you can select a file with `--config PATH`. Relative explicit paths are resolved
from your current directory. Custom YAML merges with the bundled defaults, so a
file can override only the settings you need.

For LLM settings, precedence from highest to lowest is:

1. Command-line flags
2. `DIFF2COMMIT_*` environment variables
3. Selected YAML configuration
4. Bundled defaults

| YAML setting | Default | Environment override | CLI override |
| --- | --- | --- | --- |
| `llm.base_url` | `http://localhost:11434/v1` | `DIFF2COMMIT_BASE_URL` | `--base-url` |
| `llm.model` | `diff2commit-qwen:7b` | `DIFF2COMMIT_MODEL` | `--model` |
| `llm.api_key_env` | `OLLAMA_API_KEY` | `DIFF2COMMIT_API_KEY_ENV` | `--api-key-env` |
| `llm.timeout` | `180` seconds | `DIFF2COMMIT_TIMEOUT` | `--timeout` |
| `llm.reasoning_effort` | `null` | `DIFF2COMMIT_REASONING_EFFORT` | `--reasoning-effort` |
| `max_diff_bytes` | `32000` bytes | — | — |
| `prompt.system` | Bundled commit instructions | — | — |
| `prompt.user` | Bundled diff template | — | — |

`api_key_env` names the environment variable containing the key; it is not the
key itself. Reasoning effort may be `none`, `minimal`, `low`, `medium`, `high`,
`xhigh`, or `max`, but endpoint and model support is required. YAML `null` omits
the parameter entirely; the string `none` sends it to the endpoint.

To customize the prompts, override `prompt.system` and/or `prompt.user` in YAML.
Both must be nonempty strings, and `prompt.user` must contain exactly one
`{{diff}}` placeholder. Unknown configuration keys are rejected.

### Remote endpoints

This example explicitly selects a remote endpoint. Use a model available to your
account that supports Chat Completions:

```sh
export OPENAI_API_KEY='your-api-key'
diff2commit --base-url https://api.openai.com/v1 \
  --api-key-env OPENAI_API_KEY \
  --model YOUR_MODEL_NAME \
  --dry-run
```

The repository also includes [an OpenAI configuration](configs/openai.yaml) and
[an Ollama configuration](configs/ollama.yaml). Review their model settings before
use, then select one with `--config` (use an absolute path when running in another
repository). The OpenAI example sets reasoning effort to `low` and raises the
diff limit to 200,000 bytes.

The client posts to `<base_url>/chat/completions`. Remote URLs must use HTTPS;
HTTP is allowed only for `localhost`, `127.0.0.1`, and `::1`. Credentials, query
strings, and fragments in the base URL are rejected, and redirects are blocked.

## Commit behavior and limits

- Only staged changes are used. The CLI does not stage files or push commits.
- The entire captured diff is sent to the selected endpoint. There is no secret
  redaction; review what you stage before using a remote provider.
- Oversized diffs are rejected instead of truncated. Stage a smaller change or
  raise `max_diff_bytes` in YAML, accounting for your model's context capacity.
- Binary changes appear through Git's diff metadata; binary contents are not
  included. Non-UTF-8 diff bytes are replaced when forming the model prompt.
- The CLI records the staged tree and HEAD, checks for changes during capture,
  and checks them again before committing. If either changes, rerun generation.
  These checks are not an atomic lock against concurrent Git operations.
- Commits use the existing index and normal Git hooks. Hook failures are reported.

Messages must have a Conventional Commit subject of at most 72 characters. The
accepted types are `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, and `revert`. Scope and the breaking-change marker `!`
are optional. A body must be separated from the subject by a blank line.
Validation checks format, not the accuracy of the generated description.

```text
feat(cli): add staged diff review

- Show staged files before committing
- Allow editing and regenerating the message
```

An invalid message can be edited or regenerated interactively. With `--yes` or
`--dry-run`, invalid output causes an error. Exit codes are `0` for success or
normal cancellation, `1` for handled errors, and `130` for interruption or EOF.

## Code layout and development

| File | Responsibility |
| --- | --- |
| `diff2commit/cli.py` | Argument parsing, review actions, editor integration, and orchestration |
| `diff2commit/config.py` | YAML loading, overrides, and configuration validation |
| `diff2commit/git.py` | Repository discovery, staged snapshots, file statistics, and commits |
| `diff2commit/llm.py` | HTTP requests, response normalization, and message validation |
| `diff2commit/ui.py` | Rich terminal presentation, plain output, and offline demo |
| `diff2commit/default.yaml` | Default provider settings and generation prompts |
| `configs/` | Provider examples and the Ollama Modelfile |

Install the development extras and run the available analysis tools:

```sh
python -m pip install -e '.[dev]'
ruff check .
basedpyright diff2commit
bandit -r diff2commit
```

There is currently no automated test suite in this checkout. Use
`diff2commit --help` and `diff2commit --demo` for offline CLI checks; generation
requires a configured endpoint and staged changes.
