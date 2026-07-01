"""目录内正则搜索工具。"""

from __future__ import annotations

import fnmatch
import os
import re
import typing

import agent.tool_binding

from . import _path_util as path_util


@agent.tool_binding.agent_tool(readonly=True)
def grep_search(
    agent_client: typing.Any,
    pattern: str,
    directory: str | None = None,
    filter: str | None = None,  # pylint: disable=redefined-builtin
    ignore_case: bool | None = None,
) -> str:
    """在工作区内用正则全目录搜索文件内容。用于查找符号引用、字符串、模式匹配等；取得行号后可配合 read_lines 阅读上下文。

    @param pattern: 正则表达式（搜索每行内容）
    @param directory: 搜索根目录（相对工作目录），缺省 `.`
    @param filter: 文件名通配符（fnmatch），缺省 `*`
    @param ignore_case: 是否忽略大小写
    """
    if not pattern or not pattern.strip():
        return "错误：pattern 不能为空。"

    root, directory_error = path_util.resolve_directory(
        directory,
        label="目录",
    )
    if directory_error is not None:
        return directory_error

    try:
        compiled = re.compile(
            pattern,
            re.MULTILINE | (re.IGNORECASE if ignore_case else 0),
        )
    except re.error as error:
        return f"错误：无效正则：{error}"

    output_lines: list[str] = []
    warnings: list[str] = []

    for file_path in _iter_matching_files(
        str(root),
        filter.strip() if filter else "*",
        tuple(agent_client.config.ignore_files),
    ):
        _, file_lines, file_warnings = _search_file(
            file_path, compiled, os.getcwd()
        )
        output_lines.extend(file_lines)
        warnings.extend(file_warnings)

    parts: list[str] = []
    if warnings:
        parts.append(_format_warnings(warnings))
    if output_lines:
        parts.append("\n".join(output_lines))
    if not parts:
        return "(无匹配)"
    return "\n".join(parts)


def _format_warnings(warnings: list[str]) -> str:
    if len(warnings) <= 3:
        return "\n".join(warnings)
    return f"警告：跳过 {len(warnings)} 个无法读取的文件（含非 UTF-8 或权限问题）"


def _iter_matching_files(
    root: str,
    filter_pattern: str,
    ignore_patterns: tuple[str, ...],
):
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not path_util.is_ignored_relative_path(
                f"{rel_dir}/{name}" if rel_dir else name,
                ignore_patterns,
            )
        )
        for name in sorted(filenames, key=str.lower):
            rel_file = f"{rel_dir}/{name}" if rel_dir else name
            if path_util.is_ignored_relative_path(rel_file, ignore_patterns):
                continue
            if fnmatch.fnmatch(name, filter_pattern):
                yield os.path.join(dirpath, name)


def _search_file(
    file_path: str,
    compiled: re.Pattern[str],
    rel_root: str,
) -> tuple[int, list[str], list[str]]:
    try:
        rel_path = os.path.relpath(file_path, rel_root)
    except ValueError:
        rel_path = file_path
    rel_path = rel_path.replace("\\", "/")

    warnings: list[str] = []
    try:
        with open(file_path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except UnicodeDecodeError:
        warnings.append(f"警告：跳过非 UTF-8 文件：{rel_path}")
        return 0, [], warnings
    except OSError as error:
        warnings.append(f"警告：无法读取 {rel_path}：{error}")
        return 0, [], warnings

    matched = 0
    output_lines: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        if not compiled.search(line.rstrip("\n\r")):
            continue
        content = line.rstrip("\n\r")
        output_lines.append(f"[{rel_path} line{line_no}]{content}")
        matched += 1
    return matched, output_lines, warnings
