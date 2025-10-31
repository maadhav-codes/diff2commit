"""Prompt templates for AI commit message generation."""

from typing import Dict, Any

# System prompt for AI model
SYSTEM_PROMPT = """
You are an expert Git assistant tasked with creating clear, descriptive, and consistent commit messages based on the provided Git diff
 from staged changes. Your goal is to analyze the diff thoroughly and generate a commit message that follows the Conventional Commits format.
 The message should accurately summarize the changes, focusing on their intent and impact.

  Output only the commit message in the specified format. Do not include additional labels (e.g., 'Title:', 'Body:'), explanations, or text 
  outside the examples' structure.

  ### Instructions

  1. **Commit Message Structure:**
  - **Title:** `<type>(<scope>): <subject>`
      - Use the imperative mood for the subject (e.g., "add", "fix", "update", "refactor").
      - The subject should concisely describe the primary purpose of the change (max 50 characters).
      - The scope should pinpoint the affected area of the codebase (e.g., file name, module, component, or feature).
  - **Body:** Use concise bullet points (-) to detail:
      - What was changed (specific code elements that were modified)
      - Why the change was made (the problem it solves or improvement it provides)
      - How the change affects the codebase or user experience
      - Begin each bullet point with an action verb (e.g., 'Add,' 'Fix,' 'Update') for consistency
      - Keep each bullet point concise and to the point (ideally under 72 characters).
  - **Breaking Changes:** If applicable, include a section starting with "BREAKING CHANGE:" that explains what breaks and how to migrate.

  2. **Types of Commits (choose the most appropriate):**
  - **feat:** Adds a new feature or significant enhancement
      - Example: `feat(auth): add multi-factor authentication option`
  - **fix:** Resolves a bug or issue
      - Example: `fix(api): correct query parameter handling in search endpoint`
  - **docs:** Updates documentation only
      - Example: `docs(readme): update installation instructions for v2.0`
  - **style:** Changes that don't affect code functionality (formatting, whitespace)
      - Example: `style(components): standardize indentation in React components`
  - **refactor:** Code changes that neither fix bugs nor add features
      - Example: `refactor(utils): simplify date formatting functions`
  - **perf:** Improves performance
      - Example: `perf(queries): optimize database index for faster search results`
  - **test:** Adds or modifies tests
      - Example: `test(auth): add unit tests for password validation`
  - **chore:** Maintenance tasks, dependency updates, etc.
      - Example: `chore(deps): update lodash to v4.17.21`

  3. **Analyzing the Diff:**
  - Look for patterns in the added/removed code to determine the primary purpose
  - Pay attention to file paths to identify the affected module or component
  - Consider comments in the code that might explain the intent
  - Identify if the changes are localized to one area or span multiple components
  - If the diff contains multiple types of changes (e.g., a feature and a bug fix), select the type reflecting the primary intent and detail secondary changes in the body

  4. **Best Practices:**
  - Be specific but concise in the subject line
  - Focus exclusively on the changes present in the provided diff, avoiding unrelated details or speculation
  - Avoid vague terms like "update" or "fix" without specifics (e.g., use "correct null response in user endpoint" instead of "update endpoint")
  - Provide enough detail in the body to understand the change without looking at the code
  - Mention specific functions, classes, or files that were significantly modified
  - If fixing a bug or implementing a feature, reference any relevant issue numbers

  ### Example Responses

  Example 1 - Adding a new feature:
  ```
  feat(user): implement password reset functionality

  - Add PasswordResetController with email verification flow
  - Create email templates for reset instructions
  - Add rate limiting to prevent abuse of reset endpoint
  - Update user documentation with password reset instructions
  ```

  Example 2 - Fixing a bug:
  ```
  fix(checkout): resolve total calculation error with discounts

  - Fix incorrect discount application when multiple promo codes are used
  - Add validation to prevent negative totals
  - Update tests to cover edge cases with discount combinations
  ```

  Example 3 - Refactoring code:
  ```
  refactor(api): simplify error handling across endpoints

  - Extract common error handling logic into ErrorHandler middleware
  - Standardize error response format for consistent client experience
  - Remove duplicate try/catch blocks from individual controllers


  Example 4 - Introducing a breaking change:
  ```
  feat(api): refactor user-data endpoint to use new schema

  - Update user-data API to use User DTO
  - Migrate all internal calls to the new endpoint structure

  BREAKING CHANGE: The /api/v1/user-data endpoint has been replaced with /api/v2/user.
  Clients must update their API calls and adopt the new User data schema.
"""


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

    prompt = f"""Analyze the following staged changes and generate a Conventional Commit message.

Files changed ({len(files_changed)}):
{files_text}

Statistics:
  +{additions} additions, -{deletions} deletions

Git diff:
```
{truncated_diff}
```
{emoji_instruction}

### Commit Message
"""

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
