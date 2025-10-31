"""Tests for Git operations."""

from pathlib import Path
import pytest
import git

from git.exc import InvalidGitRepositoryError

from diff2commit.git_operations import GitOperations


def test_git_operations_init(temp_git_repo: Path) -> None:
    """Test GitOperations initialization."""
    git_ops = GitOperations(str(temp_git_repo))
    assert git_ops.repo is not None


def test_git_operations_invalid_repo() -> None:
    """Test GitOperations with invalid repository."""
    with pytest.raises(InvalidGitRepositoryError):
        GitOperations("/nonexistent/path")


def test_get_staged_diff_empty(temp_git_repo: Path) -> None:
    """Test getting diff with no staged changes."""
    git_ops = GitOperations(str(temp_git_repo))
    diff_summary = git_ops.get_staged_diff()
    assert diff_summary.is_empty is True


def test_get_staged_diff_with_changes(temp_git_repo: Path) -> None:
    """Test getting diff with staged changes."""
    # Create and stage a new file
    test_file = temp_git_repo / "new_file.txt"
    test_file.write_text("New content")

    repo = git.Repo(temp_git_repo)
    repo.index.add(["new_file.txt"])

    git_ops = GitOperations(str(temp_git_repo))
    diff_summary = git_ops.get_staged_diff()

    assert diff_summary.is_empty is False
    assert "new_file.txt" in diff_summary.files_changed
    assert diff_summary.additions > 0


def test_commit_changes(temp_git_repo: Path) -> None:
    """Test committing changes."""
    # Create and stage a file
    test_file = temp_git_repo / "commit_test.txt"
    test_file.write_text("Test commit")

    repo = git.Repo(temp_git_repo)
    repo.index.add(["commit_test.txt"])

    git_ops = GitOperations(str(temp_git_repo))
    commit_sha = git_ops.commit_changes("test: add test file")

    assert commit_sha is not None
    assert len(commit_sha) == 40  # SHA-1 hash length


def test_get_repo_info(temp_git_repo: Path) -> None:
    """Test getting repository information."""
    git_ops = GitOperations(str(temp_git_repo))
    repo_info = git_ops.get_repo_info()

    assert "branch" in repo_info
    assert "remote" in repo_info
    assert "root" in repo_info
