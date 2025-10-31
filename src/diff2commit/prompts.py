"""Prompt templates for AI commit message generation."""

from typing import Dict, Any

# System prompt for AI model
SYSTEM_PROMPT = """You are an expert software engineer helping to write clear, descriptive Git commit messages.
You follow the Conventional Commits specification strictly.

Conventional Commits format:
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

Types:
- feat: A new feature
- fix: A bug fix
- docs: Documentation only changes
- style: Changes that don't affect code meaning (formatting, whitespace)
- refactor: Code change that neither fixes a bug nor adds a feature
- perf: Performance improvements
- test: Adding or modifying tests
- build: Changes to build system or dependencies
- ci: Changes to CI configuration
- chore: Other changes that don't modify src or test files
- revert: Reverts a previous commit

Rules:
1. Use lowercase for type and description
2. No period at the end of the subject line
3. Use imperative mood ("add" not "added" or "adds")
4. Subject line should be concise (max 72 characters)
5. Body should explain WHAT and WHY, not HOW
6. Separate subject from body with a blank line
7. Include breaking changes in footer with "BREAKING CHANGE:"

Respond ONLY with the commit message, no additional commentary."""


def build_commit_prompt(
    diff: str,
    files_changed: list,
    additions: int,
    deletions: int,
    change_types: Dict[str, str],
    include_emoji: bool = False,
) -> str:
    """Build the user prompt for commit message generation.

    Args:
        diff: The git diff text
        files_changed: List of changed files
        additions: Number of additions
        deletions: Number of deletions
        change_types: Dictionary mapping files to change types
        include_emoji: Whether to include emojis

    Returns:
        Formatted prompt string
    """
    # Summarize file changes
    file_summary = []
    for file in files_changed[:10]:  # Limit to first 10 files
        change_type = change_types.get(file, "M")
        file_summary.append(f"  {change_type} {file}")

    if len(files_changed) > 10:
        file_summary.append(f"  ... and {len(files_changed) - 10} more files")

    files_text = "\\n".join(file_summary)

    # Truncate diff if too long (keep first 3000 chars)
    truncated_diff = diff[:3000]
    if len(diff) > 3000:
        truncated_diff += "\\n\\n... (diff truncated)"

    emoji_instruction = ""
    if include_emoji:
        emoji_instruction = "\\nInclude an appropriate emoji at the start of the commit message."

    prompt = f"""Generate a Conventional Commit message for the following changes:

Files changed ({len(files_changed)}):
{files_text}

Statistics:
  +{additions} additions, -{deletions} deletions

Git diff:
```
{truncated_diff}
```
{emoji_instruction}

Provide a clear, concise commit message following the Conventional Commits specification.
If the changes are complex, include a body paragraph explaining the changes."""

    return prompt


def build_custom_prompt(diff: str, template: str, context: Dict[str, Any]) -> str:
    """Build a custom prompt from a template.

    Args:
        diff: The git diff text
        template: Custom template string
        context: Additional context variables

    Returns:
        Formatted prompt string
    """
    # Replace template variables
    prompt = template.format(
        diff=diff[:3000],
        files=", ".join(context.get("files_changed", [])),
        additions=context.get("additions", 0),
        deletions=context.get("deletions", 0),
        **context,
    )
    return prompt


# Example custom templates
CUSTOM_TEMPLATES = {
    "simple": """Generate a commit message for:
Files: {files}
Diff:
{diff}
""",
    "detailed": """Analyze these code changes and write a detailed commit message:

Files modified: {files}
Lines added: {additions}
Lines deleted: {deletions}

Changes:
{diff}

Include:
1. A clear summary line
2. Detailed explanation of what changed
3. Reason for the change
""",
    "jira": """Generate a commit message with JIRA ticket reference:

Ticket: {ticket_id}
Files: {files}
Changes:
{diff}

Format: [{ticket_id}] <type>: <description>
""",
}
