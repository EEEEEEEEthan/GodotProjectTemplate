"""目录遍历内置工具。"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from pathlib import Path

from egent.tool import ToolCallable


def _path_matches_any(patterns: tuple[str, ...], path_text: str) -> bool:
    return any(fnmatch.fnmatch(path_text, pattern) for pattern in patterns)


def path_available(
    path_text: str,
    whitelist: Iterable[str] | None,
    blacklist: Iterable[str] | None,
) -> bool:
    blacklist_patterns = tuple(blacklist or ())
    whitelist_patterns = tuple(whitelist or ())
    if blacklist_patterns and _path_matches_any(blacklist_patterns, path_text):
        return False
    if whitelist_patterns and not _path_matches_any(whitelist_patterns, path_text):
        return False
    return True


def get_walk_files_tool(
    whitelist: Iterable[str] | None = None,
    blacklist: Iterable[str] | None = None,
    working_directory: str | Path | None = None,
    name: str = "builtin_walk_files",
    description: str = "遍历目录文件树并缩进输出文件名。用于了解项目结构、列出目录下文件。",
) -> ToolCallable:
    """按白名单与黑名单生成预配置的目录遍历工具。"""
    whitelist_patterns = tuple(whitelist or ())
    blacklist_patterns = tuple(blacklist or ())
    resolved_working_directory = (
        Path.cwd() if working_directory is None else Path(working_directory).resolve()
    )

    def relative_path_text(path: str | Path) -> str:
        return Path(path).relative_to(resolved_working_directory).as_posix()

    def walk_files_tool(
        directory: str,
        filter: str | None = None,  # noqa: A002 pylint: disable=redefined-builtin
        depth: int | None = None,
    ) -> str:
        root = (resolved_working_directory / Path((directory or ".").strip())).resolve()
        if not root.is_relative_to(resolved_working_directory):
            return f"错误：没有权限访问目录：{directory}"
        relative_directory_text = relative_path_text(root)
        is_workspace_root = relative_directory_text == "."
        if not is_workspace_root and not path_available(
            relative_directory_text, whitelist_patterns, blacklist_patterns
        ):
            return f"错误：没有权限访问目录：{directory}"
        if not root.is_dir():
            return f"错误：目录不存在：{directory}"

        filter_pattern = (filter or "*").strip()
        max_depth = depth if depth is not None else 1
        lines: list[str] = []

        def walk_directory(directory_path: str, prefixes: tuple[bool, ...] = ()) -> None:
            if 0 < max_depth <= len(prefixes):
                return
            try:
                entries = sorted(os.scandir(directory_path), key=lambda entry: entry.name.lower())
            except OSError as error:
                lines.append(f"警告：无法访问 {directory_path}：{error}")
                return
            visible_entries: list[os.DirEntry] = []
            for entry in entries:
                if entry.is_symlink():
                    continue
                relative_entry_path = relative_path_text(entry.path)
                if not path_available(relative_entry_path, whitelist_patterns, blacklist_patterns):
                    continue
                visible_entries.append(entry)
            for index, entry in enumerate(visible_entries):
                is_last = index == len(visible_entries) - 1
                is_directory = entry.is_dir(follow_symlinks=False)
                if fnmatch.fnmatch(entry.name, filter_pattern):
                    prefix = "".join(" " if ancestor_is_last else "│" for ancestor_is_last in prefixes)
                    connector = "└ " if is_last else "├ "
                    lines.append(
                        prefix + connector + (f"{entry.name}/" if is_directory else entry.name)
                    )
                if is_directory:
                    walk_directory(entry.path, prefixes + (is_last,))

        walk_directory(str(root))
        return "(空目录)" if not lines else "\n".join(lines)

    walk_files_tool.__name__ = name
    walk_files_tool.__doc__ = (
        f"{description}\n\n"
        "@param directory 要遍历的目录\n"
        "@param filter 文件与文件夹名通配符，缺省 *\n"
        "@param depth 最大层级深度，0 表示不限制，缺省 1"
    )
    return walk_files_tool
