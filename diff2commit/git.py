import subprocess
from dataclasses import dataclass
from pathlib import Path

from .errors import ToolError


def git(root: Path, *args: str, input: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            input=input,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ToolError("Git is not installed or is not on PATH.") from exc
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ToolError(f"Git command failed: {detail}")
    return result.stdout


def repository(cwd: Path) -> Path:
    return Path(git(cwd, "rev-parse", "--show-toplevel").decode().strip())


def head(root: Path) -> bytes:
    # symbolic-ref distinguishes an unborn branch from other rev-parse failures.
    try:
        revision = git(root, "rev-parse", "--verify", "HEAD").strip()
        branch = git(root, "rev-parse", "--symbolic-full-name", "HEAD").strip()
        return revision + b":" + branch
    except ToolError:
        branch = git(root, "symbolic-ref", "-q", "HEAD").strip()
        refs = (
            git(root, "show-ref", "--heads")
            if git(root, "for-each-ref", "refs/heads").strip()
            else b""
        )
        if any(line.endswith(b" " + branch) for line in refs.splitlines()):
            raise
        return b"UNBORN:" + branch


@dataclass(frozen=True)
class FileChange:
    path: str
    added: int | None
    removed: int | None


def file_changes(numstat: bytes) -> tuple[FileChange, ...]:
    """Read Git's NUL-delimited stats, including rename paths and binary files."""
    records = iter(numstat.split(b"\0"))
    changes = []
    for record in records:
        if not record:
            continue
        added, removed, path = record.split(b"\t", 2)
        if not path:
            old, new = next(records), next(records)
            path = old + b" -> " + new
        changes.append(
            FileChange(
                path.decode("utf-8", errors="replace"),
                None if added == b"-" else int(added),
                None if removed == b"-" else int(removed),
            )
        )
    return tuple(changes)


@dataclass(frozen=True)
class Snapshot:
    diff: bytes
    tree: bytes
    head: bytes
    files: tuple[FileChange, ...] = ()


def snapshot(root: Path, limit: int) -> Snapshot:
    before = head(root)
    tree = git(root, "write-tree").strip()
    diff = git(
        root,
        "diff",
        "--staged",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--full-index",
        "--submodule=short",
        "--ignore-submodules=none",
        "--",
    )
    stats = git(
        root,
        "diff",
        "--staged",
        "--numstat",
        "-z",
        "--no-ext-diff",
        "--no-textconv",
        "--ignore-submodules=none",
        "--",
    )
    if tree != git(root, "write-tree").strip() or before != head(root):
        raise ToolError(
            "Staged changes or HEAD changed while reading the diff. Run again."
        )
    if not diff:
        raise ToolError("No staged changes. Stage files with git add first.")
    if len(diff) > limit:
        raise ToolError(
            f"Staged diff is {len(diff)} bytes, above max_diff_bytes={limit}. "
            "Stage a smaller change or increase the YAML limit."
        )
    return Snapshot(diff, tree, before, file_changes(stats))


def commit(root: Path, staged: Snapshot, message: str) -> str:
    if head(root) != staged.head or git(root, "write-tree").strip() != staged.tree:
        raise ToolError(
            "Staged changes or HEAD changed after generation. Nothing committed; run again."
        )
    # No shell, pathspec, -a, or hook bypass: only the existing index is committed.
    result = git(
        root,
        "commit",
        "--cleanup=verbatim",
        "--file=-",
        input=(message + "\n").encode(),
    )
    return result.decode("utf-8", errors="replace").strip()
