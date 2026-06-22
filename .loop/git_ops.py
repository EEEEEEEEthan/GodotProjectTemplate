"""Git 工作区操作。"""

import subprocess
from pathlib import Path


def _run_git(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_output(result: subprocess.CompletedProcess[str]) -> str:
    return (result.stdout or "") + (result.stderr or "")


def git_diff(project_root: Path) -> str:
    result = _run_git(project_root, "diff", "HEAD")
    if result.returncode != 0:
        raise RuntimeError(_git_output(result) or "git diff 失败")
    return result.stdout


def git_clean_worktree(project_root: Path) -> str:
    reset = _run_git(project_root, "reset", "--hard", "HEAD")
    clean = _run_git(project_root, "clean", "-fd")
    lines = [
        "git reset --hard HEAD:",
        _git_output(reset),
        "git clean -fd:",
        _git_output(clean),
    ]
    if reset.returncode != 0 or clean.returncode != 0:
        raise RuntimeError("\n".join(lines))
    return "\n".join(lines)


def git_commit_all(project_root: Path, message: str) -> str:
    add = _run_git(project_root, "add", "-A")
    if add.returncode != 0:
        raise RuntimeError(_git_output(add) or "git add 失败")
    commit = _run_git(project_root, "commit", "-m", message)
    lines = [
        "git add -A:",
        _git_output(add),
        "git commit:",
        _git_output(commit),
    ]
    if commit.returncode != 0:
        raise RuntimeError("\n".join(lines))
    return "\n".join(lines)


def git_push(project_root: Path) -> str:
    result = _run_git(project_root, "push")
    output = _git_output(result)
    if result.returncode != 0:
        raise RuntimeError(output or "git push 失败")
    return output
