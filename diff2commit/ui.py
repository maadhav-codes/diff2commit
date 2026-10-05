"""Rich presentation kept separate from Git, generation, and commit decisions."""

import os
import re
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import urlsplit

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from .config import Config, load_config
from .git import FileChange, Snapshot

THEME = Theme(
    {
        "accent": "bold cyan",
        "secondary": "bold magenta",
        "muted": "bright_black",
        "good": "green",
        "bad": "red",
        "warn": "yellow",
    }
)


def safe_text(value: str) -> str:
    # Treat source, model output, and paths as literal text, never terminal commands.
    return "".join(
        c
        if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159)
        else f"\\x{ord(c):02x}"
        for c in value
    )


class TerminalUI:
    def __init__(self, plain: bool = False, console: Console | None = None):
        self.console = console or Console(theme=THEME, highlight=False)
        self.errors = Console(stderr=True, theme=THEME, highlight=False)
        self.rich = (
            not plain and self.console.is_terminal and os.environ.get("TERM") != "dumb"
        )

    def note(self, message: str, style: str = "muted") -> None:
        self.errors.print(Text(safe_text(message), style=style if self.rich else None))

    def banner(self) -> None:
        brand = Text("diff", style="bold cyan")
        brand.append("2", style="bold magenta")
        brand.append("commit", style="bold cyan")
        brand.append("  /  staged changes, considered commits", style="muted")
        self.console.print()
        self.console.print(brand)
        self.console.print()

    def overview(self, root: Path, config: Config, staged: Snapshot) -> None:
        if not self.rich:
            return
        self.banner()
        branch = staged.head.decode("utf-8", errors="replace").split(":", 1)[-1]
        branch = branch.removeprefix("refs/heads/")
        if branch == "HEAD":
            branch = "detached HEAD"
        repo = Text(safe_text(root.name), style="bold")
        repo.append("\n" + safe_text(branch), style="accent")
        repo.append("\n" + safe_text(str(root)), style="muted")
        local = urlsplit(config.base_url).hostname in ("localhost", "127.0.0.1", "::1")
        model = Text(
            "LOCAL OLLAMA" if local else "REMOTE API",
            style="good" if local else "secondary",
        )
        model.append("\n" + safe_text(config.model), style="bold")
        model.append("\n" + safe_text(config.base_url), style="muted")
        if config.reasoning_effort:
            model.append("  ·  effort " + config.reasoning_effort, style="muted")
        panels = (
            Panel(
                repo,
                title="Repository",
                title_align="left",
                border_style="bright_black",
                box=box.ROUNDED,
            ),
            Panel(
                model,
                title="Provider",
                title_align="left",
                border_style="bright_black",
                box=box.ROUNDED,
            ),
        )
        if self.console.width >= 88:
            cards = Table.grid(expand=True, padding=(0, 1))
            cards.add_column(ratio=1)
            cards.add_column(ratio=1)
            cards.add_row(*panels)
            self.console.print(cards)
        else:
            self.console.print(Group(*panels))
        self.files(staged)
        self.diff(staged.diff, preview=True)

    def files(self, staged: Snapshot) -> None:
        added = sum(change.added or 0 for change in staged.files)
        removed = sum(change.removed or 0 for change in staged.files)
        summary = Text(
            f"{len(staged.files)} {'file' if len(staged.files) == 1 else 'files'}",
            style="bold",
        )
        summary.append(f"  +{added}", style="good")
        summary.append(f"  -{removed}", style="bad")
        summary.append(f"  ·  {len(staged.diff):,} bytes staged", style="muted")
        table = Table(box=None, expand=True, padding=(0, 1), show_header=False)
        table.add_column(ratio=1)
        table.add_column(justify="right", no_wrap=True)
        table.add_column(justify="right", no_wrap=True)
        for change in staged.files[:8]:
            table.add_row(
                Text(safe_text(change.path)),
                Text(
                    "binary" if change.added is None else f"+{change.added}",
                    style="good",
                ),
                Text(
                    "" if change.removed is None else f"-{change.removed}", style="bad"
                ),
            )
        if len(staged.files) > 8:
            table.add_row(
                Text(
                    f"… {len(staged.files) - 8} more files; view the full diff with d",
                    style="muted",
                )
            )
        self.console.print(
            Panel(
                Group(summary, Text(""), table),
                title="01 / Staged changes",
                title_align="left",
                border_style="cyan",
                box=box.ROUNDED,
            )
        )

    def diff(self, diff: bytes, preview: bool = False) -> None:
        text = safe_text(diff.decode("utf-8", errors="replace"))
        lines = text.splitlines()
        if not self.rich:
            self.console.print(Text(text))
            return
        # Preview is visibly limited; the model always receives the entire snapshot.
        limit = max(6, min(14, self.console.height // 3))
        preview_lines = [line for line in lines if not line.startswith("index ")]
        shown = preview_lines[:limit] if preview else lines
        subtitle = Text(
            f"{len(shown)} of {len(lines)} lines · d opens full diff"
            if len(shown) < len(lines)
            else f"{len(lines)} lines · complete diff",
            style="muted",
        )
        syntax = Syntax(
            "\n".join(shown),
            "diff",
            theme="ansi_dark",
            background_color="default",
            word_wrap=True,
            line_numbers=False,
        )
        panel = Panel(
            syntax,
            title="Staged diff",
            title_align="left",
            border_style="bright_black",
            subtitle=subtitle,
            subtitle_align="left",
            box=box.ROUNDED,
        )
        if preview:
            self.console.print(panel)
        else:
            with self.console.pager(styles=True):
                self.console.print(panel)

    def generating(self, config: Config):
        if not self.rich:
            return nullcontext()
        label = Text("Generating commit", style="accent")
        label.append("  ·  " + safe_text(config.model), style="muted")
        return self.console.status(label, spinner="dots", spinner_style="cyan")

    def message(self, message: str, error: str | None = None) -> None:
        if not self.rich:
            self.console.print(Text("\n" + safe_text(message) + "\n"))
            if error:
                self.note(f"Message needs editing: {error}")
            return
        content = Text(safe_text(message))
        subject = message.splitlines()[0] if message else ""
        content.stylize("bold", 0, len(safe_text(subject)))
        match = re.match(r"[a-z]+(?:\([^\n)]*\))?!?:", safe_text(subject))
        if match:
            content.stylize("accent", 0, match.end())
        for match in re.finditer(r"(?m)^- ", content.plain):
            content.stylize("secondary", match.start(), match.end())
        for match in re.finditer(r"(?m)^BREAKING CHANGE:", content.plain):
            content.stylize("warn", match.start(), match.end())
        title = Text("02 / Commit message", style="bold")
        status = Text(
            "Needs editing" if error else "Conventional Commit ✓",
            style="warn" if error else "good",
        )
        self.console.print(
            Panel(
                content,
                title=title,
                title_align="left",
                subtitle=status,
                subtitle_align="right",
                border_style="yellow" if error else "cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        if error:
            self.console.print(Text(safe_text(error), style="warn"))

    def actions(self, hint: bool = True) -> None:
        if self.rich:
            actions = Text()
            for key, label in (
                ("a", "accept"),
                ("e", "edit"),
                ("r", "regenerate"),
                ("d", "diff"),
                ("q", "quit"),
            ):
                if actions.plain:
                    actions.append("   ")
                actions.append(
                    f" {key} ",
                    style="bold black on cyan" if key == "a" else "bold cyan",
                )
                actions.append(" " + label)
            self.console.print(actions)
            if hint:
                self.console.print(
                    Text(
                        "Enter cancels · choose a key, then press Enter", style="muted"
                    )
                )

    def action(self) -> str:
        self.actions()
        return (
            input(
                "› "
                if self.rich
                else "[a]ccept / [e]dit / [r]egenerate / [d]iff / [q]uit (default q): "
            )
            .strip()
            .lower()
        )

    def success(self, output: str) -> None:
        if self.rich:
            self.console.print(
                Panel(
                    Text(safe_text(output)),
                    title="Committed",
                    title_align="left",
                    border_style="green",
                    box=box.ROUNDED,
                )
            )
        else:
            self.console.print(Text(safe_text(output)))

    def help(self, parser) -> None:
        if not self.rich:
            parser.print_help()
            return
        self.banner()
        help_text = Text(parser.format_help())
        for match in re.finditer(r"--[a-z-]+", help_text.plain):
            help_text.stylize("accent", match.start(), match.end())
        self.console.print(
            Panel(
                help_text,
                title="Usage",
                title_align="left",
                border_style="bright_black",
                box=box.ROUNDED,
            )
        )
        self.console.print(
            Text("Try diff2commit --demo for an offline UI preview.", style="muted")
        )

    def demo(self) -> None:
        config = load_config(
            None,
            {"base_url": "http://localhost:11434/v1", "model": "diff2commit-qwen:7b"},
        )
        diff = b"""diff --git a/src/cli.py b/src/cli.py
--- a/src/cli.py
+++ b/src/cli.py
@@ -24,3 +24,6 @@ def review(message):
-    print(message)
-    return input("Accept? ")
+    console.print(Panel(message, title="Commit message"))
+    console.print(Syntax(staged_diff, "diff"))
+    return prompt("Accept / Edit / Regenerate / Diff / Quit")
diff --git a/pyproject.toml b/pyproject.toml
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -8,1 +8,1 @@
-dependencies = ["PyYAML>=6"]
+dependencies = ["PyYAML>=6", "rich>=14"]
"""
        staged = Snapshot(
            diff,
            b"demo",
            b"demo:refs/heads/feat/terminal-ui",
            (FileChange("src/cli.py", 3, 2), FileChange("pyproject.toml", 1, 1)),
        )
        self.overview(Path("~/projects/diff2commit"), config, staged)
        if not self.rich:
            self.diff(diff)
        self.message(
            "feat(cli): add rich commit review\n\n- Highlight staged changes and file statistics\n- Add message panels and a full-diff viewer\n- Keep redirected output plain"
        )
        self.actions(hint=False)
        self.note("Demo only · no Git commands, model requests, or commits.")
