"""目录树遍历工具。"""

from __future__ import annotations

import fnmatch
import functools
import os
import typing

from . import _path_util as path_util


def walk_files(
    agent_client: typing.Any,
    directory: str,
    filter: str | None = None,  # pylint: disable=redefined-builtin
    depth: int | None = None,
) -> str:
    """遍历目录文件树并缩进输出文件名。用于了解项目结构、列出目录下文件。

    @param directory: 要遍历的目录（相对工作目录）
    @param filter: 文件与文件夹名通配符，缺省 `*`
    @param depth: 最大层级深度，0 表示不限制，缺省 1
    """
    root, directory_error = path_util.resolve_directory(
        directory,
        label="目录",
        display=directory,
    )
    if directory_error is not None:
        return directory_error

    ignore_patterns = tuple(agent_client.config.ignore_files)
    filter_pattern = filter.strip() if filter else "*"
    max_depth = depth if depth is not None else 1
    output_lines: list[str] = []
    _walk_files(
        str(root),
        filter_pattern,
        ignore_patterns,
        max_depth,
        output_lines,
    )
    if not output_lines:
        return "(空目录)"
    return "\n".join(output_lines)


def _is_ignored(name: str, ignore_patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch.fnmatch(name, pattern) for pattern in ignore_patterns
    )


@functools.lru_cache(maxsize=None)
def _has_matching_descendants(
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
            if entry.is_dir(follow_symlinks=False) and _has_matching_descendants(
                entry.path, filter_pattern, ignore_patterns
            ):
                return True
    except OSError:
        return False
    return False


def _should_show(
    entry: os.DirEntry[str],
    filter_pattern: str,
    ignore_patterns: tuple[str, ...],
) -> bool:
    if fnmatch.fnmatch(entry.name, filter_pattern):
        return True
    return (
        entry.is_dir(follow_symlinks=False)
        and filter_pattern != "*"
        and _has_matching_descendants(
            entry.path, filter_pattern, ignore_patterns
        )
    )


def _should_recurse(
    entry: os.DirEntry[str],
    filter_pattern: str,
    ignore_patterns: tuple[str, ...],
) -> bool:
    if not entry.is_dir(follow_symlinks=False):
        return False
    if filter_pattern == "*":
        return True
    if fnmatch.fnmatch(entry.name, filter_pattern):
        return True
    return _has_matching_descendants(
        entry.path, filter_pattern, ignore_patterns
    )


def _format_prefix(prefixes: list[bool]) -> str:
    return "".join(" " if last else "│" for last in prefixes)


def _walk_files(
    root: str,
    filter_pattern: str,
    ignore_patterns: tuple[str, ...],
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
        if not _is_ignored(entry.name, ignore_patterns)
        and (entry.is_dir(follow_symlinks=False) or entry.is_file(follow_symlinks=False))
    ]
    entries = [
        entry
        for entry in entries
        if _should_show(entry, filter_pattern, ignore_patterns)
        or _should_recurse(entry, filter_pattern, ignore_patterns)
    ]

    for index, entry in enumerate(entries):
        is_last = index == len(entries) - 1
        show = _should_show(entry, filter_pattern, ignore_patterns)

        if show:
            connector = "└ " if is_last else "├ "
            name = entry.name + "/" if entry.is_dir(follow_symlinks=False) else entry.name
            output_lines.append(
                _format_prefix(prefixes) + connector + name
            )

        if _should_recurse(entry, filter_pattern, ignore_patterns):
            _walk_files(
                entry.path,
                filter_pattern,
                ignore_patterns,
                max_depth,
                output_lines,
                prefixes + [is_last],
            )
