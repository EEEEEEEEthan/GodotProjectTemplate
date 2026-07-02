"""只读内置工具。"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterable
from pathlib import Path

from egent.limits import TOOL_RESULT_MAX_CHARS
from egent.tool import ToolCallable

_READ_FILE_MAX_CHARS = TOOL_RESULT_MAX_CHARS * 9 // 10


def get_walk_files_tool(
    whitelist: Iterable[str] | None = None,
    blacklist: Iterable[str] | None = None,
    working_directory: str | Path | None = None,
    name: str = "builtin_walk_files",
    description: str = "遍历目录文件树并缩进输出文件名",
) -> ToolCallable:
    """按白名单与黑名单生成预配置的目录遍历工具。"""
    whitelist_patterns = tuple(whitelist or ())
    blacklist_patterns = tuple(blacklist or ())
    resolved_working_directory = (
        Path.cwd() if working_directory is None else Path(working_directory).resolve()
    )

    def relative_path_text(path: str | Path) -> str:
        return Path(path).relative_to(resolved_working_directory).as_posix()

    def path_available(path_text: str) -> bool:
        def path_matches_any(patterns: tuple[str, ...]) -> bool:
            return any(fnmatch.fnmatch(path_text, pattern) for pattern in patterns)

        if blacklist_patterns and path_matches_any(blacklist_patterns):
            return False
        if whitelist_patterns and not path_matches_any(whitelist_patterns):
            return False
        return True

    def walk_files(
        directory: str,
        filter: str | None = None,  # noqa: A002 pylint: disable=redefined-builtin
        depth: int | None = None,
    ) -> str:
        root = (resolved_working_directory / Path((directory or ".").strip())).resolve()
        if not root.is_relative_to(resolved_working_directory):
            return f"错误：没有权限访问目录：{directory}"
        relative_directory_text = relative_path_text(root)
        if relative_directory_text != "." and not path_available(relative_directory_text):
            return f"错误：没有权限访问目录：{directory}"
        if not root.is_dir():
            return f"错误：目录不存在：{directory}"
        max_depth = depth if depth is not None else 1
        filter_pattern = (filter or "*").strip()
        lines: list[str] = []

        def walk_directory(
            directory_path: str,
            ancestor_is_last_flags: tuple[bool, ...] = (),
        ) -> None:
            if 0 < max_depth <= len(ancestor_is_last_flags):
                return
            try:
                entries = sorted(os.scandir(directory_path), key=lambda entry: entry.name.lower())
            except OSError as error:
                lines.append(f"警告：无法访问 {directory_path}：{error}")
                return
            visible_entries = [
                entry
                for entry in entries
                if path_available(relative_path_text(entry.path))
            ]
            for index, entry in enumerate(visible_entries):
                is_last_entry = index == len(visible_entries) - 1
                is_symlink = entry.is_symlink()
                is_directory = entry.is_dir(follow_symlinks=False) or is_symlink
                if fnmatch.fnmatch(entry.name, filter_pattern):
                    prefix = "".join(
                        " " if ancestor_is_last else "│"
                        for ancestor_is_last in ancestor_is_last_flags
                    )
                    connector = "└ " if is_last_entry else "├ "
                    display_name = f"{entry.name}/" if is_directory else entry.name
                    if is_symlink:
                        display_name += " #symlink"
                    lines.append(prefix + connector + display_name)
                if is_directory:
                    walk_directory(entry.path, ancestor_is_last_flags + (is_last_entry,))

        walk_directory(str(root))
        return "(空目录)" if not lines else "\n".join(lines)

    walk_files.__name__ = name
    walk_files.__doc__ = (
        f"{description}\n\n"
        "@param directory 要遍历的目录\n"
        "@param filter 文件与文件夹名通配符，缺省 *\n"
        "@param depth 最大层级深度，0 表示不限制，缺省 1"
    )
    return walk_files


def read_file(
    path: str,
    offset: int | None = None,
    limit: int | None = None,
) -> str:
    """读取指定文件内容

    @param path 要读取的文件路径
    @param offset 起始行号，从 1 开始，缺省 1
    @param limit 读取行数，缺省读取到文件末尾
    """
    file_path = Path(path.strip()).resolve()
    if not file_path.is_file():
        return f"错误：文件不存在：{path}"
    try:
        text = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return f"错误：无法以 UTF-8 解码文件：{path}"
    except OSError as error:
        return f"错误：读取文件失败：{path}：{error}"

    lines = text.splitlines(keepends=True)
    start = max((offset or 1) - 1, 0)
    if limit is not None:
        lines = lines[start : start + max(limit, 0)]
    elif start:
        lines = lines[start:]
    if not lines:
        return "(空文件)"
    content = "".join(lines)
    if len(content) <= _READ_FILE_MAX_CHARS:
        return content
    remaining = len(content) - _READ_FILE_MAX_CHARS
    return (
        f"{content[:_READ_FILE_MAX_CHARS]}...\n"
        f"(内容太长被截断，剩余{remaining}字符)"
    )
