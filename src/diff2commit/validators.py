"""Validators for commit messages."""

import re
from typing import Tuple, List, Optional


class CommitMessageValidator:
    """Validate commit messages against various standards."""

    # Conventional Commits types
    CONVENTIONAL_TYPES = [
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "build",
        "ci",
        "chore",
        "revert",
    ]

    def __init__(self, max_subject_length: int = 72):
        """Initialize validator.

        Args:
            max_subject_length: Maximum allowed subject line length
        """
        self.max_subject_length = max_subject_length

    def validate_conventional(self, message: str) -> Tuple[bool, List[str]]:
        """Validate message against Conventional Commits specification.

        Args:
            message: Commit message to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        lines = message.split("\\n")

        if not lines:
            return False, ["Message is empty"]

        subject = lines[0]

        # Check type prefix
        type_pattern = r"^(" + "|".join(self.CONVENTIONAL_TYPES) + r")(\\([a-z0-9-]+\\))?: .+"
        if not re.match(type_pattern, subject):
            errors.append(
                f"Subject must start with a valid type: {', '.join(self.CONVENTIONAL_TYPES)}"
            )

        # Check subject length
        if len(subject) > self.max_subject_length:
            errors.append(f"Subject exceeds {self.max_subject_length} characters ({len(subject)})")

        # Check for period at end of subject
        if subject.endswith("."):
            errors.append("Subject should not end with a period")

        # Check for imperative mood (basic check)
        if re.match(
            r"^(\\w+)(\\([^)]+\\))?: (added|fixed|changed|updated)", subject, re.IGNORECASE
        ):
            errors.append("Use imperative mood (add, fix, change) not past tense")

        # Check blank line after subject if body exists
        if len(lines) > 1 and lines[1] != "":
            errors.append("Separate subject from body with a blank line")

        return len(errors) == 0, errors

    def validate_subject_length(self, subject: str) -> bool:
        """Validate subject line length.

        Args:
            subject: Subject line

        Returns:
            True if valid length
        """
        return len(subject) <= self.max_subject_length

    def validate_body_line_length(self, body: str, max_length: int = 100) -> Tuple[bool, List[int]]:
        """Validate body line lengths.

        Args:
            body: Message body
            max_length: Maximum line length

        Returns:
            Tuple of (all_valid, list_of_invalid_line_numbers)
        """
        lines = body.split("\\n")
        invalid_lines = []

        for i, line in enumerate(lines, start=1):
            if len(line) > max_length:
                invalid_lines.append(i)

        return len(invalid_lines) == 0, invalid_lines

    def extract_breaking_changes(self, message: str) -> Optional[str]:
        """Extract breaking change information from message.

        Args:
            message: Commit message

        Returns:
            Breaking change description or None
        """
        # Check for BREAKING CHANGE in footer
        pattern = r"BREAKING CHANGE: (.+?)(?:\\n|$)"
        match = re.search(pattern, message, re.MULTILINE)

        if match:
            return match.group(1)

        # Check for ! in type
        if re.match(r"^\\w+!\\(", message) or re.match(r"^\\w+!:", message):
            return "Breaking change indicated in subject"

        return None

    def suggest_type(self, diff: str) -> str:
        """Suggest a commit type based on diff content.

        Args:
            diff: Git diff text

        Returns:
            Suggested commit type
        """
        diff_lower = diff.lower()

        # Check for test files
        if re.search(r"test_|_test\\.|spec\\.", diff_lower):
            return "test"

        # Check for documentation
        if re.search(r"readme|doc|comment", diff_lower):
            return "docs"

        # Check for configuration/build files
        if re.search(r"package\\.json|requirements|setup\\.py|dockerfile", diff_lower):
            return "build"

        # Check for CI files
        if re.search(r"\\.github/workflows|\\.gitlab-ci", diff_lower):
            return "ci"

        # Check for bug-related keywords
        if re.search(r"fix|bug|issue|error|crash", diff_lower):
            return "fix"

        # Default to feat
        return "feat"
