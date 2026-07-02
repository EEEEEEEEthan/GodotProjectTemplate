"""目录遍历内置工具。"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from pathlib import Path

from egent.tool import ToolCallable


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

    def path_matches(patterns: tuple[str, ...], path_text: str) -> bool:
        return any(fnmatch.fnmatch(path_text, pattern) for pattern in patterns)

    def walk_files_tool(
        directory: str,
        filter: str | None = None,  # noqa: A002 pylint: disable=redefined-builtin
        depth: int | None = None,
    ) -> str:
        root = (resolved_working_directory / Path((directory or ".").strip())).resolve()
        if not root.is_relative_to(resolved_working_directory):
            return f"错误：目录超出工作目录范围：{directory}"
        relative_directory_text = relative_path_text(root)
        if relative_directory_text != "." and path_matches(blacklist_patterns, relative_directory_text):
            return f"错误：目录命中黑名单：{directory}"
        if (
            whitelist_patterns
            and relative_directory_text != "."
            and not path_matches(whitelist_patterns, relative_directory_text)
        ):
            return f"错误：目录不在白名单内：{directory}"
        if not root.is_dir():
            return f"错误：目录不存在：{directory}"

        filter_pattern = (filter or "*").strip()
        max_depth = depth if depth is not None else 1
        lines: list[str] = []

        def walk_directory(directory_path: str, prefixes: list[bool] | None = None) -> None:
            if prefixes is None:
                prefixes = []
            if 0 < max_depth <= len(prefixes):
                return

            try:
                entries = sorted(os.scandir(directory_path), key=lambda entry: entry.name.lower())
            except OSError as error:
                lines.append(f"警告：无法访问 {directory_path}：{error}")
                return

            visible_entries: list[tuple[os.DirEntry, str]] = []
            for entry in entries:
                if entry.is_symlink():
                    continue
                relative_entry_path = relative_path_text(entry.path)
                if path_matches(blacklist_patterns, relative_entry_path):
                    continue
                visible_entries.append((entry, relative_entry_path))

            for index, (entry, relative_entry_path) in enumerate(visible_entries):
                is_last = index == len(visible_entries) - 1
                matches_filter = filter_pattern == "*" or fnmatch.fnmatch(entry.name, filter_pattern)
                matches_whitelist = (
                    not whitelist_patterns
                    or path_matches(whitelist_patterns, relative_entry_path)
                )
                is_directory = entry.is_dir(follow_symlinks=False)
                if matches_filter and matches_whitelist:
                    prefix = "".join(" " if ancestor_is_last else "│" for ancestor_is_last in prefixes)
                    connector = "└ " if is_last else "├ "
                    display_name = f"{entry.name}/" if is_directory else entry.name
                    lines.append(prefix + connector + display_name)
                if is_directory:
                    walk_directory(entry.path, prefixes + [is_last])

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
