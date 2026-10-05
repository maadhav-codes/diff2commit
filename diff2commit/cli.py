import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import REASONING_EFFORTS, default_yaml, load_config
from .errors import ToolError
from .git import commit, git, repository, snapshot
from .llm import generate, normalize, validate
from .ui import TerminalUI


class HelpAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        TerminalUI(plain=namespace.plain).help(parser)
        parser.exit()


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generate and review a Conventional Commit from staged Git changes.",
        add_help=False,
    )
    p.add_argument(
        "--plain", action="store_true", help="disable panels, colors, and animations"
    )
    p.add_argument(
        "-h",
        "--help",
        action=HelpAction,
        nargs=0,
        help="show this help message and exit",
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument(
        "--init",
        action="store_true",
        help="write a starter YAML config without overwriting",
    )
    mode.add_argument(
        "--demo",
        action="store_true",
        help="preview the terminal UI offline; no Git or LLM calls",
    )
    p.add_argument(
        "--config",
        type=Path,
        help="YAML config (default: repository .diff2commit.yaml)",
    )
    p.add_argument("--model", help="model name for the configured endpoint")
    p.add_argument("--base-url", help="OpenAI-compatible API base URL")
    p.add_argument("--api-key-env", help="environment variable containing the API key")
    p.add_argument("--timeout", type=float, help="request timeout in seconds")
    p.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        help="reasoning effort for models supporting this API parameter",
    )
    mode.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="accept and commit a valid generated message",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="print a valid generated message without committing",
    )
    p.add_argument(
        "--save-diff",
        type=Path,
        help="save the exact diff to a new file (otherwise kept in memory)",
    )
    return p


def write_new(path: Path, content: bytes) -> None:
    # Restrictive permissions because diffs can contain private source code.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(content)


def edit(root: Path, message: str) -> str:
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if not editor:
        editor = git(root, "var", "GIT_EDITOR").decode().strip()
    # Arguments are supported (e.g. code --wait) without executing a shell.
    command = shlex.split(editor)
    if not command:
        raise ToolError(
            "Set VISUAL or EDITOR to an editor command, such as 'code --wait'."
        )
    with tempfile.TemporaryDirectory(prefix="diff2commit-") as directory:
        path = Path(directory) / "COMMIT_EDITMSG"
        path.write_text(message + "\n", encoding="utf-8")
        result = subprocess.run([*command, str(path)], check=False)
        if result.returncode:
            raise ToolError("Editor exited unsuccessfully. Nothing committed.")
        return normalize(path.read_text(encoding="utf-8"))


def review(root: Path, config, staged, ui: TerminalUI | None = None) -> str | None:
    ui = ui or TerminalUI()
    with ui.generating(config):
        message = generate(config, staged.diff)
    while True:
        error = None
        try:
            validate(message)
        except ToolError as exc:
            error = str(exc)
        ui.message(message, error)
        action = ui.action()
        if action in ("", "q", "quit"):
            return None
        if action in ("a", "accept"):
            if error is None:
                return message
        elif action in ("e", "edit"):
            message = edit(root, message)
        elif action in ("r", "regenerate"):
            with ui.generating(config):
                message = generate(config, staged.diff)
        elif action in ("d", "diff"):
            ui.diff(staged.diff)
        else:
            ui.note("Choose a, e, r, d, or q.", style="warn")


def run(args) -> int:
    ui = TerminalUI(plain=args.plain)
    if args.demo:
        ui.demo()
        return 0
    if args.init:
        path = args.config or Path.cwd() / ".diff2commit.yaml"
        write_new(path, default_yaml().encode())
        print(f"Created {path}. Review the LLM settings before generating.")
        return 0
    root = repository(Path.cwd())
    path = args.config
    if path is None and (root / ".diff2commit.yaml").exists():
        path = root / ".diff2commit.yaml"
    config = load_config(path, vars(args))
    staged = snapshot(root, config.max_diff_bytes)
    if args.save_diff:
        write_new(args.save_diff, staged.diff)
    if not args.yes and not args.dry_run and not sys.stdin.isatty():
        raise ToolError(
            "Interactive review requires a terminal. Use --dry-run to print or --yes to commit."
        )
    if not ui.rich or args.yes or args.dry_run:
        ui.note(
            f"Sending {len(staged.diff)} staged diff bytes to {config.base_url} (model: {config.model})."
        )
    if args.yes or args.dry_run:
        message = generate(config, staged.diff)
        validate(message)
        print(message)
        if args.dry_run:
            return 0
    else:
        ui.overview(root, config, staged)
        message = review(root, config, staged, ui)
        if message is None:
            print("Cancelled. Nothing committed.")
            return 0
    ui.success(commit(root, staged, message))
    return 0


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.", file=sys.stderr)
        return 130
    except (ToolError, OSError, UnicodeError, ValueError) as exc:
        TerminalUI(plain=args.plain).note(f"diff2commit: {exc}", style="bad")
        return 1
