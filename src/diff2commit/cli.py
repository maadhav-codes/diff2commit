"""Main CLI application."""

from typing import Dict, Optional, Literal, Type, cast

import typer

from diff2commit.ai_providers.anthropic_provider import AnthropicProvider
from diff2commit.ai_providers.base import AIProvider
from diff2commit.ai_providers.gemini_provider import GeminiProvider
from diff2commit.ai_providers.openai_provider import OpenAIProvider
from diff2commit.config import Diff2CommitConfig, load_config
from diff2commit.git_operations import GitOperations
from diff2commit.ui.console import (
    create_progress,
    display_commit_message,
    display_diff_summary,
    print_error,
    print_info,
    print_warning,
    print_success,
    console,
)
from diff2commit.ui.interactive import InteractiveEditor
from diff2commit.usage_tracker import UsageTracker

from diff2commit.__version__ import __version__

app = typer.Typer(
    name="diff2commit",
    help="CLI tool that automatically generates clear, descriptive commit messages from staged Git diffs using AI",
    add_completion=True,
    no_args_is_help=True,
)

AIProviderType = Literal["openai", "anthropic", "gemini"]


def get_provider(config: Diff2CommitConfig) -> AIProvider:
    """Get the appropriate AI provider based on configuration."""
    providers: Dict[str, Type[AIProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "gemini": GeminiProvider,
    }
    provider_class = providers.get(config.ai_provider)
    if not provider_class:
        raise ValueError(f"Unknown provider: {config.ai_provider}")
    return provider_class(config)


@app.command()
def generate(
    review: bool = typer.Option(
        True, "--review/--no-review", help="Review message before committing"
    ),
    count: int = typer.Option(
        1, "--count", "-c", min=1, max=5, help="Number of message suggestions to generate"
    ),
    provider: Optional[str] = typer.Option(
        None, "--provider", "-p", help="Override AI provider (openai, anthropic, gemini)"
    ),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Override AI model"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    no_commit: bool = typer.Option(
        False, "--no-commit", help="Generate message without committing"
    ),
) -> None:
    """Generate and commit with AI-powered message."""
    try:
        # Load configuration
        config = load_config()

        # Override config with CLI options
        if provider:
            # Validate and cast provider type
            if provider not in ("openai", "anthropic", "gemini"):
                print_error(f"Invalid provider: {provider}. Must be openai, anthropic, or gemini.")
                raise typer.Exit(1)
            config.ai_provider = cast(AIProviderType, provider)

        if model:
            config.ai_model = model

        if verbose:
            config.verbose = verbose

        # Initialize Git operations
        try:
            git_ops = GitOperations()
        except Exception as e:
            print_error(str(e))
            raise typer.Exit(1)

        # Get repository info
        if config.verbose:
            repo_info = git_ops.get_repo_info()
            print_info(f"Repository: {repo_info['root']}")
            print_info(f"Branch: {repo_info['branch']}")

        # Check for staged changes
        if not git_ops.has_staged_changes():
            print_error("No staged changes found. Use 'git add' to stage changes first.")
            raise typer.Exit(1)

        # Get diff summary
        diff_summary = git_ops.get_staged_diff()

        # Display diff summary
        display_diff_summary(
            diff_summary.files_changed,
            diff_summary.additions,
            diff_summary.deletions,
            diff_summary.change_types,
        )

        # Initialize AI provider
        try:
            ai_provider = get_provider(config)
        except ValueError as e:
            print_error(str(e))
            print_info("Set your API key: export D2C_API_KEY='your-key-here'")
            raise typer.Exit(1)

        # Generate commit messages
        messages = []
        usage_tracker = UsageTracker() if config.track_usage else None

        with create_progress() as progress:
            task = progress.add_task(f"[cyan]Generating {count} commit message(s)...", total=count)

            for i in range(count):
                try:
                    context = {
                        "files_changed": diff_summary.files_changed,
                        "additions": diff_summary.additions,
                        "deletions": diff_summary.deletions,
                        "change_types": diff_summary.change_types,
                    }

                    commit_msg = ai_provider.generate_commit_message(
                        diff_summary.diff_text, context
                    )

                    messages.append(commit_msg.format())

                    # Track usage
                    if usage_tracker:
                        usage_tracker.record_usage(
                            provider=commit_msg.provider,
                            model=commit_msg.model,
                            tokens=commit_msg.tokens_used,
                            cost=commit_msg.cost,
                            success=True,
                        )

                    if config.verbose:
                        print_info(
                            f"Generated message {i+1}: {commit_msg.tokens_used} tokens, ${commit_msg.cost:.4f}"
                        )

                except Exception as e:
                    print_error(f"Failed to generate message {i+1}: {e}")
                    if usage_tracker:
                        usage_tracker.record_usage(
                            provider=config.ai_provider,
                            model=config.ai_model,
                            tokens=0,
                            cost=0,
                            success=False,
                        )

                progress.update(task, advance=1)

        if not messages:
            print_error("Failed to generate any commit messages.")
            raise typer.Exit(1)

        # Review and edit (if enabled)
        if review:
            editor = InteractiveEditor()
            final_message = editor.review_and_edit(messages)

            if not final_message:
                print_warning("Commit cancelled by user.")
                raise typer.Exit(0)
        else:
            final_message = messages[0]
            display_commit_message(final_message)

        # Commit or just display
        if no_commit:
            print_info("Message generated (not committed):")
            console.print(final_message)
        else:
            try:
                commit_sha = git_ops.commit_changes(final_message)
                print_success(f"Changes committed successfully! ({commit_sha[:7]})")

                if config.verbose:
                    console.print(f"\n[dim]Commit SHA: {commit_sha}[/dim]")

            except Exception as e:
                print_error(f"Failed to commit: {e}")
                print_info("Your message was:")
                console.print(final_message)
                raise typer.Exit(1)

    except typer.Exit:
        raise
    except KeyboardInterrupt:
        print_warning("\nOperation cancelled by user.")
        raise typer.Exit(130)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        if config.verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1)


@app.command()
def usage(
    monthly: bool = typer.Option(False, "--monthly", help="Show only current month usage"),
    by_provider: bool = typer.Option(False, "--by-provider", help="Group by provider"),
) -> None:
    """Display token usage and cost statistics."""
    try:
        tracker = UsageTracker()

        if monthly:
            stats = tracker.get_monthly_usage()
            console.print(f"\n[bold]📊 Usage for {stats['month']}[/bold]\n")
            console.print(f"  Requests: {stats['requests']}")
            console.print(f"  Tokens: {stats['tokens']:,}")
            console.print(f"  Cost: ${stats['cost']:.4f}\n")

        elif by_provider:
            providers = tracker.get_usage_by_provider()
            console.print("\n[bold]📊 Usage by Provider[/bold]\n")

            for p in providers:
                console.print(f"[cyan]{p['provider']}[/cyan] ({p['model']})")
                console.print(f"  Requests: {p['requests']}")
                console.print(f"  Tokens: {p['tokens']:,}")
                console.print(f"  Cost: ${p['cost']:.4f}\n")

        else:
            total = tracker.get_total_usage()
            console.print("\n[bold]📊 Total Usage Statistics[/bold]\n")
            console.print(f"  Total Requests: {total['total_requests']}")
            console.print(f"  Successful: {total['successful_requests']}")
            console.print(f"  Total Tokens: {total['total_tokens']:,}")
            console.print(f"  Total Cost: ${total['total_cost']:.4f}\n")

    except Exception as e:
        print_error(f"Failed to retrieve usage statistics: {e}")
        raise typer.Exit(1)


@app.command()
def config() -> None:
    """Display current configuration."""
    try:
        cfg = load_config()

        console.print("\n[bold]⚙️  Current Configuration[/bold]\n")
        console.print(f"  AI Provider: [cyan]{cfg.ai_provider}[/cyan]")
        console.print(f"  AI Model: {cfg.ai_model}")
        console.print(f"  Max Tokens: {cfg.max_tokens}")
        console.print(f"  Temperature: {cfg.temperature}")
        console.print(f"  Commit Format: {cfg.commit_format}")
        console.print(f"  Max Subject Length: {cfg.max_subject_length}")
        console.print(f"  Track Usage: {cfg.track_usage}")

        if cfg.api_key:
            masked_key = cfg.api_key[:8] + "..." + cfg.api_key[-4:]
            console.print(f"  API Key: {masked_key}")
        else:
            console.print("  API Key: [red]Not set[/red]")

        console.print(f"\n[dim]Config file: {cfg.get_config_path()}[/dim]")
        console.print(f"[dim]Usage database: {cfg.get_usage_db_path()}[/dim]\n")

    except Exception as e:
        print_error(f"Failed to load configuration: {e}")
        raise typer.Exit(1)


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"\n[bold cyan]diff2commit[/bold cyan] version [green]{__version__}[/green]\n")


def main() -> None:
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
