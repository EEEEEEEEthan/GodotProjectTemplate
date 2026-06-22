"""Git 清理：仅编排器调用，agent 通过标记请求。"""

import subprocess
from pathlib import Path


def git_is_clean(project_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and not result.stdout.strip()


def git_diff(project_root: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "") + (result.stdout or "") or "git diff 失败")
    return result.stdout


def git_clean_worktree(project_root: Path) -> str:
    reset = subprocess.run(
        ["git", "reset", "--hard", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    clean = subprocess.run(
        ["git", "clean", "-fd"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [
        "git reset --hard HEAD:",
        reset.stdout + reset.stderr,
        "git clean -fd:",
        clean.stdout + clean.stderr,
    ]
    if reset.returncode != 0 or clean.returncode != 0:
        raise RuntimeError("\n".join(lines))
    return "\n".join(lines)
