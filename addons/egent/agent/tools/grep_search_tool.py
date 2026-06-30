"""目录内正则搜索工具。"""

from __future__ import annotations

import fnmatch
import os
import re
import typing

from . import _path_util as path_util


def grep_search(
    agent_client: typing.Any,
    pattern: str,
    directory: str | None = None,
    filter: str | None = None,  # pylint: disable=redefined-builtin
    ignore_case: bool | None = None,
    max_matches: int | None = None,
) -> str:
    """在工作区内用正则全目录搜索文件内容。用于查找符号引用、字符串、模式匹配等；取得行号后可配合 read_lines 阅读上下文。

    @param pattern: 正则表达式（搜索每行内容）
    @param directory: 搜索根目录（相对工作目录），缺省 `.`
    @param filter: 文件名通配符（fnmatch），缺省 `*`
    @param ignore_case: 是否忽略大小写
    @param max_matches: 最多输出匹配行数，缺省 500
    """
    if not pattern or not pattern.strip():
        return "错误：pattern 不能为空。"

    root, directory_error = path_util.resolve_directory(
        directory,
        label="目录",
    )
    if directory_error is not None:
        return directory_error

    filter_pattern = filter.strip() if filter else "*"
    match_limit = max_matches if max_matches is not None else 500
    if match_limit < 1:
        return "错误：max_matches 必须 >= 1"

    flags = re.MULTILINE
    if ignore_case:
        flags |= re.IGNORECASE
    try:
        compiled = re.compile(pattern, flags)
    except re.error as error:
        return f"错误：无效正则：{error}"

    ignore_patterns = tuple(agent_client.config.ignore_files)
    output_lines: list[str] = []
    warnings: list[str] = []
    cwd = os.getcwd()
    total = 0
    truncated = False

    for file_path in _iter_matching_files(str(root), filter_pattern, ignore_patterns):
        remaining = match_limit - total
        if remaining <= 0:
            truncated = True
            break
        matched, file_truncated, file_lines, file_warnings = _search_file(
            file_path, compiled, cwd, remaining
        )
        output_lines.extend(file_lines)
        warnings.extend(file_warnings)
        total += matched
        if file_truncated:
            truncated = True
            break

    if truncated:
        warnings.append(f"（已达上限 {match_limit} 条，结果已截断）")

    parts: list[str] = []
    if warnings:
        parts.append("\n".join(warnings))
    if output_lines:
        parts.append("\n".join(output_lines))
    if not parts:
        return "(无匹配)"
    return "\n".join(parts)


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
    remaining: int,
) -> tuple[int, bool, list[str], list[str]]:
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
        return 0, False, [], warnings
    except OSError as error:
        warnings.append(f"警告：无法读取 {rel_path}：{error}")
        return 0, False, [], warnings

    matched = 0
    output_lines: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        if not compiled.search(line.rstrip("\n\r")):
            continue
        content = line.rstrip("\n\r")
        output_lines.append(f"[{rel_path} line{line_no}]{content}")
        matched += 1
        if matched >= remaining:
            return matched, True, output_lines, warnings
    return matched, False, output_lines, warnings
