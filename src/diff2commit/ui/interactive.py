"""Interactive editor for reviewing and modifying commit messages."""

from typing import Optional, List
from prompt_toolkit import prompt
from rich.prompt import Confirm, Prompt

from diff2commit.ui import console
from diff2commit.ui.console import display_commit_message


class InteractiveEditor:
    """Interactive editor for commit messages."""

    def __init__(self):
        """Initialize the interactive editor."""
        self.current_message = ""

    def review_and_edit(self, messages: List[str], show_diff: bool = True) -> Optional[str]:
        """Review and optionally edit commit message(s).

        Args:
            messages: List of generated commit messages
            show_diff: Whether to show diff summary

        Returns:
            Selected/edited message or None if cancelled
        """
        if not messages:
            console.print("[red]No commit messages generated.[/red]")
            return None

        # If multiple messages, let user choose
        if len(messages) > 1:
            selected = self._select_message(messages)
            if selected is None:
                return None
            message = messages[selected]
        else:
            message = messages[0]

        self.current_message = message

        # Display the message
        display_commit_message(message, "Generated Commit Message")

        # Get user action
        return self._get_user_action()

    def _select_message(self, messages: List[str]) -> Optional[int]:
        """Let user select from multiple messages.

        Args:
            messages: List of messages

        Returns:
            Index of selected message or None
        """
        console.print("\\n[bold]Multiple suggestions generated:[/bold]\\n")

        for i, msg in enumerate(messages, 1):
            # Show first line (subject) of each
            subject = msg.split("\\n")[0]
            console.print(f"  [cyan]{i}.[/cyan] {subject}")

        console.print()

        try:
            choice = Prompt.ask(
                "Select a message",
                choices=[str(i) for i in range(1, len(messages) + 1)],
                default="1",
            )
            return int(choice) - 1
        except (KeyboardInterrupt, EOFError):
            return None

    def _get_user_action(self) -> Optional[str]:
        """Get user action (accept, edit, regenerate, cancel).

        Returns:
            Final message or None if cancelled
        """
        console.print("\\n[bold]What would you like to do?[/bold]")
        console.print("  [green]a[/green] - Accept and commit")
        console.print("  [yellow]e[/yellow] - Edit message")
        console.print("  [blue]r[/blue] - Regenerate (exit and run again)")
        console.print("  [red]c[/red] - Cancel")

        try:
            action = Prompt.ask("\\nYour choice", choices=["a", "e", "r", "c"], default="a")

            if action == "a":
                return self.current_message
            elif action == "e":
                return self._edit_message()
            elif action == "r":
                console.print("[blue]Please run the command again to regenerate.[/blue]")
                return None
            else:  # cancel
                console.print("[red]Commit cancelled.[/red]")
                return None

        except (KeyboardInterrupt, EOFError):
            console.print("\\n[red]Commit cancelled.[/red]")
            return None

    def _edit_message(self) -> Optional[str]:
        """Allow user to edit the message.

        Returns:
            Edited message or None
        """
        console.print("\\n[yellow]Edit the commit message (press Enter twice when done):[/yellow]")
        console.print("[dim]Tip: Keep the first line under 72 characters[/dim]\\n")

        lines = []
        try:
            # Read multiple lines
            console.print(self.current_message)
            console.print("\\n[yellow]Enter your edited message:[/yellow]")

            while True:
                line = prompt("> " if not lines else "  ")
                if not line and lines:
                    # Empty line and we have content, finish
                    break
                if line or lines:  # Add line if not first empty line
                    lines.append(line)

            edited = "\\n".join(lines).strip()

            if edited:
                self.current_message = edited
                display_commit_message(edited, "Edited Commit Message")

                if Confirm.ask("Use this message?", default=True):
                    return edited

            return None

        except (KeyboardInterrupt, EOFError):
            console.print("\\n[red]Edit cancelled.[/red]")
            return None

    def simple_confirm(self, message: str) -> bool:
        """Simple yes/no confirmation.

        Args:
            message: Message to display

        Returns:
            True if confirmed
        """
        console.print(f"\\n{message}")
        return Confirm.ask("Commit with this message?", default=True)
