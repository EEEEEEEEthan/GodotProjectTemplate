"""目录树遍历工具。"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

IGNORED_NAMES = frozenset({
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".godot",
    ".cursor",
    ".claude",
    ".agents",
})


def walk_files(
    directory: str,
    filter: str | None = None,  # noqa: A002 pylint: disable=redefined-builtin
    depth: int | None = None,
) -> str:
    """遍历目录文件树并缩进输出文件名。用于了解项目结构、列出目录下文件。

    @param directory 要遍历的目录（相对工作目录）
    @param filter 文件与文件夹名通配符，缺省 *
    @param depth 最大层级深度，0 表示不限制，缺省 1
    """
    relative_directory = Path((directory or ".").strip())
    if relative_directory.is_absolute():
        return f"错误：目录必须是相对工作目录的路径，不接受绝对路径：{directory}"

    root = (Path.cwd() / relative_directory).resolve()
    if not root.is_dir():
        return f"错误：目录不存在：{directory}"

    filter_pattern = (filter or "*").strip()
    max_depth = depth if depth is not None else 1
    lines: list[str] = []

    def walk_directory(root: str, prefixes: list[bool] | None = None) -> None:
        if prefixes is None:
            prefixes = []
        if 0 < max_depth <= len(prefixes):
            return

        try:
            entries = sorted(os.scandir(root), key=lambda entry: entry.name.lower())
        except OSError as error:
            lines.append(f"警告：无法访问 {root}：{error}")
            return

        visible_entries = [
            entry
            for entry in entries
            if entry.name not in IGNORED_NAMES
            and not entry.is_symlink()
        ]
        for index, entry in enumerate(visible_entries):
            is_last = index == len(visible_entries) - 1
            matches_filter = (
                filter_pattern == "*"
                or fnmatch.fnmatch(entry.name, filter_pattern)
            )
            if matches_filter:
                prefix = "".join(" " if last else "│" for last in prefixes)
                connector = "└ " if is_last else "├ "
                if entry.is_dir(follow_symlinks=False):
                    name = f"{entry.name}/"
                else:
                    name = entry.name
                lines.append(prefix + connector + name)
            if entry.is_dir(follow_symlinks=False):
                walk_directory(entry.path, prefixes + [is_last])

    walk_directory(str(root))
    return "(空目录)" if not lines else "\n".join(lines)
