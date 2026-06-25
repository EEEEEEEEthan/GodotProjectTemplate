"""目录内正则搜索工具。"""

from __future__ import annotations

import fnmatch
import os
import pathlib
import re

import agent.tools._path_util

DEFAULT_SKIP_DIRS = frozenset({".git", "bin", "obj", "node_modules", ".vs", "__pycache__"})


class GrepSearchTool:
    """在工作区内用正则搜索文件内容。"""

    @staticmethod
    def grep_search(
        pattern: str,
        directory: str | None = None,
        filter: str | None = None,  # pylint: disable=redefined-builtin
        ignore_case: bool | None = None,
        max_matches: int | None = None,
    ) -> str:
        """在目录树内用正则搜索文件内容。"""
        if not pattern or not pattern.strip():
            return "错误：pattern 不能为空。"

        directory_text = directory.strip() if directory else "."
        relative_directory, directory_error = agent.tools._path_util.resolve_relative_path(
            directory_text,
            label="目录",
        )
        if directory_error is not None:
            return directory_error

        root = (pathlib.Path.cwd() / relative_directory).resolve()
        if not root.is_dir():
            return f"错误：目录不存在：{directory_text}"

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

        output_lines: list[str] = []
        warnings: list[str] = []
        cwd = os.getcwd()
        total = 0
        truncated = False

        for file_path in GrepSearchTool.__iter_matching_files(str(root), filter_pattern):
            remaining = match_limit - total
            if remaining <= 0:
                truncated = True
                break
            matched, file_truncated, file_lines, file_warnings = (
                GrepSearchTool.__search_file(file_path, compiled, cwd, remaining)
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

    @staticmethod
    def __iter_matching_files(root: str, filter_pattern: str):
        root = os.path.abspath(root)
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(
                name for name in dirnames if name not in DEFAULT_SKIP_DIRS
            )
            for name in sorted(filenames, key=str.lower):
                if fnmatch.fnmatch(name, filter_pattern):
                    yield os.path.join(dirpath, name)

    @staticmethod
    def __search_file(
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
