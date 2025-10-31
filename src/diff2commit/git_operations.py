"""Git operations for retrieving diffs and committing changes."""

from typing import List, Dict
from dataclasses import dataclass
import git
from git.exc import GitCommandError, InvalidGitRepositoryError


@dataclass
class DiffSummary:
    """Summary of Git diff."""

    files_changed: List[str]
    additions: int
    deletions: int
    diff_text: str
    change_types: Dict[str, str]
    is_empty: bool


class GitOperations:
    """Handle Git repository operations."""

    def __init__(self, repo_path: str = "."):
        """Initialize Git operations.

        Args:
            repo_path: Path to Git repository (default: current directory)

        Raises:
            InvalidGitRepositoryError: If not a valid Git repository
        """
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except (InvalidGitRepositoryError, git.NoSuchPathError) as e:
            raise InvalidGitRepositoryError(
                f"Not a git repository: {repo_path}. Please run 'git init' first."
            ) from e

    def get_staged_diff(self) -> DiffSummary:
        """Get summary of staged changes.

        Returns:
            DiffSummary object containing staged changes

        Raises:
            ValueError: If no staged changes found
        """
        # Get staged changes
        try:
            diff_index = self.repo.index.diff("HEAD", create_patch=True)
        except GitCommandError:
            # No HEAD yet (initial commit)
            diff_index = self.repo.index.diff(None, create_patch=True)

        if not diff_index:
            return DiffSummary(
                files_changed=[],
                additions=0,
                deletions=0,
                diff_text="",
                change_types={},
                is_empty=True,
            )

        files_changed = []
        change_types = {}

        for diff_item in diff_index:
            file_path = diff_item.b_path or diff_item.a_path
            files_changed.append(file_path)
            change_types[file_path] = diff_item.change_type

        # Get full diff text
        try:
            full_diff = self.repo.git.diff("--staged")
        except GitCommandError:
            # Initial commit
            full_diff = self.repo.git.diff("--staged", "--cached")

        # Count additions and deletions
        additions = full_diff.count("\\n+") - full_diff.count("\\n+++")
        deletions = full_diff.count("\\n-") - full_diff.count("\\n---")

        return DiffSummary(
            files_changed=files_changed,
            additions=max(0, additions),
            deletions=max(0, deletions),
            diff_text=full_diff,
            change_types=change_types,
            is_empty=False,
        )

    def commit_changes(self, message: str) -> str:
        """Commit staged changes with the given message.

        Args:
            message: Commit message

        Returns:
            Commit SHA hash

        Raises:
            GitCommandError: If commit fails
        """
        try:
            commit = self.repo.index.commit(message)
            return commit.hexsha
        except GitCommandError as e:
            raise GitCommandError(f"Failed to commit changes: {e}") from e

    def get_repo_info(self) -> Dict[str, str]:
        """Get repository information.

        Returns:
            Dictionary with repository info
        """
        try:
            branch = self.repo.active_branch.name
        except TypeError:
            branch = "detached HEAD"

        return {
            "branch": branch,
            "remote": self._get_remote_url(),
            "root": self.repo.working_dir or "",
        }

    def _get_remote_url(self) -> str:
        """Get remote URL if available."""
        try:
            if self.repo.remotes:
                return str(self.repo.remotes.origin.url)
        except (AttributeError, ValueError):
            pass
        return "no remote"

    def has_staged_changes(self) -> bool:
        """Check if there are staged changes.

        Returns:
            True if there are staged changes
        """
        diff_summary = self.get_staged_diff()
        return not diff_summary.is_empty
