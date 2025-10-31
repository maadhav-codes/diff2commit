"""Custom exceptions for diff2commit CLI."""


class AICommitError(Exception):
    """Base exception for diff2commit errors."""

    pass


class GitRepositoryError(AICommitError):
    """Raised when Git repository operations fail."""

    pass


class NoStagedChangesError(AICommitError):
    """Raised when no staged changes are found."""

    pass


class AIProviderError(AICommitError):
    """Raised when AI provider operations fail."""

    pass


class ConfigurationError(AICommitError):
    """Raised when configuration is invalid."""

    pass


class CostLimitExceededError(AICommitError):
    """Raised when cost limit is exceeded."""

    pass


class InvalidCommitMessageError(AICommitError):
    """Raised when commit message validation fails."""

    pass
