"""目录树遍历工具。"""

from __future__ import annotations

import fnmatch
import functools
import os
import typing

from . import _path_util as path_util
from . import _schema_util as schema_util

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "walk_files_tool_walk_files": schema_util.function_schema(
        "walk_files_tool_walk_files",
        "遍历目录文件树并缩进输出文件名。用于了解项目结构、列出目录下文件",
        {
            "directory": {
                "type": "string",
                "description": "要遍历的目录（相对工作目录）",
            },
            "filter": {
                "type": "string",
                "description": "文件与文件夹名通配符，缺省 *",
            },
            "depth": {
                "type": "integer",
                "description": "最大层级深度，0 表示不限制，缺省 1",
            },
        },
        required=["directory"],
    ),
}


class WalkFilesTool:
    """深度优先遍历目录并缩进输出文件名。"""

    def __init__(self, agent: typing.Any) -> None:
        self.__ignore_patterns = tuple(agent.config.ignore_files)

    def walk_files(
        self,
        directory: str,
        filter: str | None = None,  # pylint: disable=redefined-builtin
        depth: int | None = None,
    ) -> str:
        """遍历目标目录下的文件与文件夹。"""
        root, directory_error = path_util.resolve_directory(
            directory,
            label="目录",
            display=directory,
        )
        if directory_error is not None:
            return directory_error

        filter_pattern = filter.strip() if filter else "*"
        max_depth = depth if depth is not None else 1
        output_lines: list[str] = []
        self.__walk_files(
            str(root),
            filter_pattern,
            max_depth,
            output_lines,
        )
        if not output_lines:
            return "(空目录)"
        return "\n".join(output_lines)

    def __is_ignored(self, name: str) -> bool:
        return any(
            fnmatch.fnmatch(name, pattern) for pattern in self.__ignore_patterns
        )

    @staticmethod
    @functools.lru_cache(maxsize=None)
    def __has_matching_descendants(
        path: str,
        filter_pattern: str,
        ignore_patterns: tuple[str, ...],
    ) -> bool:
        if filter_pattern == "*":
            return True
        try:
            for entry in os.scandir(path):
                if any(fnmatch.fnmatch(entry.name, pattern) for pattern in ignore_patterns):
                    continue
                if entry.is_file(follow_symlinks=False) and fnmatch.fnmatch(
                    entry.name, filter_pattern
                ):
                    return True
                if entry.is_dir(follow_symlinks=False) and WalkFilesTool.__has_matching_descendants(
                    entry.path, filter_pattern, ignore_patterns
                ):
                    return True
        except OSError:
            return False
        return False

    def __should_show(self, entry: os.DirEntry[str], filter_pattern: str) -> bool:
        if fnmatch.fnmatch(entry.name, filter_pattern):
            return True
        return (
            entry.is_dir(follow_symlinks=False)
            and filter_pattern != "*"
            and self.__has_matching_descendants(
                entry.path, filter_pattern, self.__ignore_patterns
            )
        )

    def __should_recurse(self, entry: os.DirEntry[str], filter_pattern: str) -> bool:
        if not entry.is_dir(follow_symlinks=False):
            return False
        if filter_pattern == "*":
            return True
        if fnmatch.fnmatch(entry.name, filter_pattern):
            return True
        return self.__has_matching_descendants(
            entry.path, filter_pattern, self.__ignore_patterns
        )

    @staticmethod
    def __format_prefix(prefixes: list[bool]) -> str:
        return "".join(" " if last else "│" for last in prefixes)

    def __walk_files(
        self,
        root: str,
        filter_pattern: str,
        max_depth: int,
        output_lines: list[str],
        prefixes: list[bool] | None = None,
    ) -> None:
        if prefixes is None:
            prefixes = []

        if 0 < max_depth <= len(prefixes):
            return

        try:
            entries = sorted(os.scandir(root), key=lambda entry: entry.name.lower())
        except OSError as error:
            output_lines.append(f"警告：无法访问 {root}：{error}")
            return

        entries = [
            entry
            for entry in entries
            if not self.__is_ignored(entry.name)
            and (entry.is_dir(follow_symlinks=False) or entry.is_file(follow_symlinks=False))
        ]
        entries = [
            entry
            for entry in entries
            if self.__should_show(entry, filter_pattern)
            or self.__should_recurse(entry, filter_pattern)
        ]

        for index, entry in enumerate(entries):
            is_last = index == len(entries) - 1
            show = self.__should_show(entry, filter_pattern)

            if show:
                connector = "└ " if is_last else "├ "
                name = entry.name + "/" if entry.is_dir(follow_symlinks=False) else entry.name
                output_lines.append(
                    WalkFilesTool.__format_prefix(prefixes) + connector + name
                )

            if self.__should_recurse(entry, filter_pattern):
                self.__walk_files(
                    entry.path,
                    filter_pattern,
                    max_depth,
                    output_lines,
                    prefixes + [is_last],
                )
