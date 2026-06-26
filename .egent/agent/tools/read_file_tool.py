"""项目内文本文件读取工具。"""

from __future__ import annotations

import pathlib
import re
import typing

from . import _cs_outline as cs_outline
from . import _output_util as output_util
from . import _path_util as path_util

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

# ---------- Python outline ----------
_PY_DECORATOR_RE = re.compile(r"^\s*@(\w+(?:\.\w+)*)")
_PY_CLASS_RE = re.compile(r"^\s*class\s+(\w+)\s*(?:\((.+?)\))?\s*:")
_PY_FUNC_RE = re.compile(
    r"^\s*(?:(async)\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(.+?))?\s*:"
)
_PY_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(\S+)")
_PY_MODULE_VAR_RE = re.compile(r"^(\w+)\s*=")


def _py_outline_text(lines: list[str]) -> str:
    """解析 Python 源文件文本并生成大纲。"""
    output_lines: list[str] = []
    output_lines.append("行尾的尖括号表示行号")
    # stack: (indent, kind, name, line_no)
    scope_stack: list[tuple[int, str, str, int]] = []
    indent_unit = 4  # assume 4-space indent

    def _peek_scope_indent() -> int:
        return scope_stack[-1][0] if scope_stack else 0

    def _pop_to_indent(col: int) -> None:
        while scope_stack and scope_stack[-1][0] >= col:
            scope_stack.pop()

    pending_decorators: list[str] = []

    for line_no, raw_line in enumerate(lines, start=1):
        stripped_raw = raw_line.rstrip("\n\r")
        # skip blank lines and full-line comments
        if not stripped_raw.strip() or stripped_raw.strip().startswith("#"):
            continue

        stripped = stripped_raw.expandtabs(4)
        leading_space = len(stripped) - len(stripped.lstrip())
        col = leading_space

        content = stripped.strip()
        if not content or content.startswith("#"):
            continue

        # Close scopes that are deeper than current indent
        if col <= _peek_scope_indent() and scope_stack:
            _pop_to_indent(col)

        # Decorator: stash it for the next class/func
        dec_match = _PY_DECORATOR_RE.match(content)
        if dec_match:
            pending_decorators.append(f"@{dec_match.group(1)}")
            continue

        # Class definition
        cls_match = _PY_CLASS_RE.match(content)
        if cls_match:
            _pop_to_indent(col)
            name = cls_match.group(1)
            bases = cls_match.group(2)
            if bases:
                label = f"class {name}({bases})"
            else:
                label = f"class {name}"
            indent_prefix = "\t" * (col // indent_unit)
            # emit any pending decorators
            for dec in pending_decorators:
                output_lines.append(indent_prefix + f"{dec} <{line_no}>")
            pending_decorators.clear()
            output_lines.append(indent_prefix + f"{label} <{line_no}>")
            scope_stack.append((col, "class", name, line_no))
            continue

        # Function / method definition
        func_match = _PY_FUNC_RE.match(content)
        if func_match:
            _pop_to_indent(col)
            is_async = func_match.group(1)
            name = func_match.group(2)
            params = func_match.group(3)
            ret = func_match.group(4)
            prefix = "async " if is_async else ""
            label = f"{prefix}def {name}({params})"
            if ret:
                label += f" -> {ret}"
            indent_prefix = "\t" * (col // indent_unit)
            # emit any pending decorators
            for dec in pending_decorators:
                output_lines.append(indent_prefix + f"{dec} <{line_no}>")
            pending_decorators.clear()
            output_lines.append(indent_prefix + f"{label} <{line_no}>")
            scope_stack.append((col, "function", name, line_no))
            continue

        # If we see a non-decorator, non-class, non-func line, flush pending decorators
        # (they were orphan decorators not attached to anything)
        pending_decorators.clear()

        # Module-level import (only at indent 0)
        if col == 0:
            imp_match = _PY_IMPORT_RE.match(content)
            if imp_match:
                output_lines.append(f"    import {imp_match.group(1)} <{line_no}>")
                continue

        # Module-level variable assignment (only at indent 0)
        if col == 0:
            var_match = _PY_MODULE_VAR_RE.match(content)
            if var_match:
                output_lines.append(f"    {var_match.group(1)} = ... <{line_no}>")
                continue

    return "\n".join(output_lines)


class ReadFileTool:
    """读取工作区内文本文件。"""

    def __init__(self, agent: typing.Any) -> None:
        self._agent = agent

    def read_file_outline_cs(self, file_path: str) -> str:
        """读取 C# 源文件大纲（namespace / 类型 / 成员）。阅读 .cs 文件时先读大纲。

        @param file_path: C# 源文件路径（相对工作目录）
        """
        absolute_path, resolve_error = self.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error

        warning = ""
        if absolute_path.suffix.lower() != ".cs":
            warning = f"警告：文件扩展名不是 .cs：{file_path}\n"

        try:
            lines = absolute_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as error:
            return f"错误：无法读取文件：{error}"

        return warning + cs_outline.outline_cs_text(lines)

    def read_file_outline_md(self, file_path: str) -> str:
        """读取 Markdown 文件标题大纲。阅读 .md 文件时先读大纲。

        @param file_path: Markdown 文件路径（相对工作目录）
        """
        absolute_path, resolve_error = self.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error

        warning = ""
        if absolute_path.suffix.lower() != ".md":
            warning = f"警告：文件扩展名不是 .md：{file_path}\n"

        try:
            with absolute_path.open(encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as error:
            return f"错误：无法读取文件：{error}"

        output_lines = ["行尾的尖括号表示行号"]
        for line_no, raw_line in enumerate(lines, start=1):
            match = HEADING_RE.match(raw_line.rstrip("\n\r"))
            if not match:
                continue
            level = len(match.group(1))
            title = match.group(2).strip()
            output_lines.append("\t" * (level - 1) + f"{title} <{line_no}>")
        return warning + "\n".join(output_lines)

    def read_file_outline_py(self, file_path: str) -> str:
        """读取 Python 源文件大纲（类 / 函数 / 顶层赋值）。阅读 .py 文件时先读大纲。

        @param file_path: Python 文件路径（相对工作目录）
        """
        absolute_path, resolve_error = self.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error

        warning = ""
        if absolute_path.suffix.lower() not in (".py", ".pyi", ".pyx"):
            warning = f"警告：文件扩展名不是 .py：{file_path}\n"

        try:
            with absolute_path.open(encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as error:
            return f"错误：无法读取文件：{error}"

        return warning + _py_outline_text(lines)

    def read_lines(self, file_path: str, start_line: int, end_line: int) -> str:
        """按行号范围读取文件片段（1-based，含首尾）。通常在 grep_search 或大纲取得行号后使用。

        @param file_path: 文件路径（相对工作目录）
        @param start_line: 起始行号（1-based，含）
        @param end_line: 结束行号（1-based，含）
        """
        absolute_path, resolve_error = self.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error
        if start_line < 1:
            return "错误：起始行号必须 >= 1"
        if end_line < start_line:
            return "错误：结束行号不能小于起始行号"

        try:
            lines = absolute_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as error:
            return f"错误：无法读取文件：{error}"

        total = len(lines)
        if start_line > total:
            return f"错误：起始行号 {start_line} 超出文件总行数 {total}"

        clamped_end = min(end_line, total)
        content = "".join(lines[line_no - 1] for line_no in range(start_line, clamped_end + 1))
        return output_util.truncate_output(content)

    def read_whole_file(self, file_path: str) -> str:
        """读取文件全文。用于非 .cs/.md 文件，或大纲策略无法定位细节时的 fallback。

        @param file_path: 文件路径（相对工作目录）
        """
        absolute_path, resolve_error = self.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error
        try:
            content = absolute_path.read_text(encoding="utf-8")
        except OSError as error:
            return f"错误：无法读取文件：{error}"
        return output_util.truncate_output(content)

    def __resolve_file(self, file_path: str) -> tuple[pathlib.Path | None, str | None]:
        relative_path, path_error = path_util.resolve_relative_path(
            file_path,
            label="文件路径",
        )
        if path_error is not None:
            return None, path_error
        absolute_path = (pathlib.Path.cwd() / relative_path).resolve()
        if not absolute_path.is_file():
            return None, f"错误：文件不存在：{file_path}"
        return absolute_path, None
