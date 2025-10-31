"""Rich console utilities for beautiful terminal output."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Dict, Any

# Global console instance
console = Console()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]✗ Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✓ Success:[/bold green] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[bold blue]ℹ Info:[/bold blue] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[bold yellow]⚠ Warning:[/bold yellow] {message}")


def display_diff_summary(
    files_changed: list, additions: int, deletions: int, change_types: Dict[str, str]
) -> None:
    """Display a summary of the diff."""
    console.print("\\n[bold]📝 Staged Changes:[/bold]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Status", style="dim", width=8)
    table.add_column("File")

    # Change type symbols
    symbols = {
        "A": "[green]✚[/green] Added",
        "M": "[yellow]●[/yellow] Modified",
        "D": "[red]✖[/red] Deleted",
        "R": "[blue]→[/blue] Renamed",
    }

    for file in files_changed[:20]:  # Show max 20 files
        change_type = change_types.get(file, "M")
        symbol = symbols.get(change_type, "[dim]●[/dim] Changed")
        table.add_row(symbol, file)

    if len(files_changed) > 20:
        table.add_row("[dim]...[/dim]", f"[dim]and {len(files_changed) - 20} more files[/dim]")

    console.print(table)
    console.print(
        f"\\n[dim]Stats: [green]+{additions}[/green] additions, [red]-{deletions}[/red] deletions[/dim]\\n"
    )


def display_commit_message(message: str, title: str = "Generated Commit Message") -> None:
    """Display a commit message with syntax highlighting."""
    syntax = Syntax(message, "git-commit", theme="monokai", line_numbers=False)
    panel = Panel(
        syntax, title=f"[bold cyan]{title}[/bold cyan]", border_style="cyan", padding=(1, 2)
    )
    console.print(panel)


def display_usage_stats(stats: Dict[str, Any]) -> None:
    """Display token usage and cost statistics."""
    table = Table(title="[bold]📊 Usage Statistics[/bold]", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    for key, value in stats.items():
        table.add_row(key, str(value))

    console.print(table)


def create_progress() -> Progress:
    """Create a progress indicator."""
    return Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
    )
