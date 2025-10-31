"""Pytest configuration and fixtures."""

import pytest
import shutil
import git
from pathlib import Path
from typing import Iterator

from diff2commit.config import Diff2CommitConfig


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary Git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    repo = git.Repo.init(repo_path)

    # Configure git
    with repo.config_writer() as config:
        config.set_value("user", "name", "Test User")
        config.set_value("user", "email", "test@example.com")

    # Create initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    yield repo_path

    # Cleanup
    shutil.rmtree(repo_path, ignore_errors=True)


@pytest.fixture
def mock_config() -> Diff2CommitConfig:
    """Create a mock configuration for testing."""
    return Diff2CommitConfig(
        ai_provider="openai",
        ai_model="gpt-4",
        api_key="test-api-key",
        max_tokens=200,
        temperature=0.7,
        track_usage=False,
    )


@pytest.fixture
def sample_diff() -> str:
    """Sample Git diff for testing."""
    return """diff --git a/src/main.py b/src/main.py
index 1234567..abcdefg 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1,5 +1,8 @@
 def main():
-    print("Hello World")
+    print("Hello, World!")
+
+def greet(name):
+    return f"Hello, {name}!"

 if __name__ == "__main__":
     main()
"""


@pytest.fixture
def sample_commit_message() -> str:
    """Sample commit message for testing."""
    return """feat: add greeting function

Implement a new greeting function that accepts a name parameter.
Also update the main function to use proper punctuation.
"""
