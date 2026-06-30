"""项目内文本文件读取工具。"""

from __future__ import annotations

import pathlib
import re
import typing

from . import _cs_outline as cs_outline
from . import _output_util as output_util
from . import _path_util as path_util

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")

_PY_DECORATOR_RE = re.compile(r"^\s*@(\w+(?:\.\w+)*)")
_PY_CLASS_RE = re.compile(r"^\s*class\s+(\w+)\s*(?:\((.+?)\))?\s*:")
_PY_FUNC_RE = re.compile(
    r"^\s*(?:(async)\s+)?def\s+(\w+)\s*\(([^)]*)\)\s*(?:->\s*(.+?))?\s*:"
)
_PY_IMPORT_RE = re.compile(r"^\s*(?:import|from)\s+(\S+)")
_PY_MODULE_VAR_RE = re.compile(r"^(\w+)\s*=")


def read_file_outline_cs(agent_client: typing.Any, file_path: str) -> str:
    """读取 C# 源文件大纲（namespace / 类型 / 成员）。阅读 .cs 文件时先读大纲。

    @param file_path: C# 源文件路径（相对工作目录）
    """
    del agent_client
    return _read_outline_file(file_path, (".cs",), cs_outline.outline_cs_text)


def read_file_outline_md(agent_client: typing.Any, file_path: str) -> str:
    """读取 Markdown 文件标题大纲。阅读 .md 文件时先读大纲。

    @param file_path: Markdown 文件路径（相对工作目录）
    """
    del agent_client
    return _read_outline_file(file_path, (".md",), _md_outline_text)


def read_file_outline_py(agent_client: typing.Any, file_path: str) -> str:
    """读取 Python 源文件大纲（类 / 函数 / 顶层赋值）。阅读 .py 文件时先读大纲。

    @param file_path: Python 文件路径（相对工作目录）
    """
    del agent_client
    return _read_outline_file(file_path, (".py", ".pyi", ".pyx"), _py_outline_text)


def read_lines(
    agent_client: typing.Any,
    file_path: str,
    start_line: int,
    end_line: int,
) -> str:
    """按行号范围读取文件片段（1-based，含首尾）。通常在 grep_search 或大纲取得行号后使用。

    @param file_path: 文件路径（相对工作目录）
    @param start_line: 起始行号（1-based，含）
    @param end_line: 结束行号（1-based，含）
    """
    del agent_client
    absolute_path, resolve_error = _resolve_file(file_path)
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


def read_whole_file(agent_client: typing.Any, file_path: str) -> str:
    """读取文件全文。用于非 .cs/.md 文件，或大纲策略无法定位细节时的 fallback。

    @param file_path: 文件路径（相对工作目录）
    """
    del agent_client
    absolute_path, resolve_error = _resolve_file(file_path)
    if resolve_error is not None:
        return resolve_error
    try:
        content = absolute_path.read_text(encoding="utf-8")
    except OSError as error:
        return f"错误：无法读取文件：{error}"
    return output_util.truncate_output(content)


def _read_outline_file(
    file_path: str,
    expected_suffixes: tuple[str, ...],
    formatter: typing.Callable[[list[str]], str],
) -> str:
    """共享辅助函数：路径解析、后缀检查、文件读取、格式化输出。"""
    absolute_path, resolve_error = _resolve_file(file_path)
    if resolve_error is not None:
        return resolve_error

    warning = ""
    if absolute_path.suffix.lower() not in expected_suffixes:
        warning = f"警告：文件扩展名不是 {expected_suffixes[0]}：{file_path}\n"

    try:
        lines = absolute_path.read_text(encoding="utf-8").splitlines(keepends=True)
    except OSError as error:
        return f"错误：无法读取文件：{error}"

    return warning + formatter(lines)


def _resolve_file(file_path: str) -> tuple[pathlib.Path | None, str | None]:
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


def _py_outline_text(lines: list[str]) -> str:
    output_lines: list[str] = []
    output_lines.append("行尾的尖括号表示行号")
    scope_stack: list[tuple[int, str, str, int]] = []
    indent_unit = 4

    def peek_scope_indent() -> int:
        return scope_stack[-1][0] if scope_stack else 0

    def pop_to_indent(column: int) -> None:
        while scope_stack and scope_stack[-1][0] >= column:
            scope_stack.pop()

    pending_decorators: list[str] = []

    for line_no, raw_line in enumerate(lines, start=1):
        stripped_raw = raw_line.rstrip("\n\r")
        if not stripped_raw.strip() or stripped_raw.strip().startswith("#"):
            continue

        stripped = stripped_raw.expandtabs(4)
        leading_space = len(stripped) - len(stripped.lstrip())
        column = leading_space

        content = stripped.strip()
        if not content or content.startswith("#"):
            continue

        if column <= peek_scope_indent() and scope_stack:
            pop_to_indent(column)

        decorator_match = _PY_DECORATOR_RE.match(content)
        if decorator_match:
            pending_decorators.append(f"@{decorator_match.group(1)}")
            continue

        class_match = _PY_CLASS_RE.match(content)
        if class_match:
            pop_to_indent(column)
            name = class_match.group(1)
            bases = class_match.group(2)
            label = f"class {name}({bases})" if bases else f"class {name}"
            indent_prefix = "\t" * (column // indent_unit)
            for decorator in pending_decorators:
                output_lines.append(indent_prefix + f"{decorator} <{line_no}>")
            pending_decorators.clear()
            output_lines.append(indent_prefix + f"{label} <{line_no}>")
            scope_stack.append((column, "class", name, line_no))
            continue

        function_match = _PY_FUNC_RE.match(content)
        if function_match:
            pop_to_indent(column)
            is_async = function_match.group(1)
            name = function_match.group(2)
            params = function_match.group(3)
            return_type = function_match.group(4)
            prefix = "async " if is_async else ""
            label = f"{prefix}def {name}({params})"
            if return_type:
                label += f" -> {return_type}"
            indent_prefix = "\t" * (column // indent_unit)
            for decorator in pending_decorators:
                output_lines.append(indent_prefix + f"{decorator} <{line_no}>")
            pending_decorators.clear()
            output_lines.append(indent_prefix + f"{label} <{line_no}>")
            scope_stack.append((column, "function", name, line_no))
            continue

        pending_decorators.clear()

        if column == 0:
            import_match = _PY_IMPORT_RE.match(content)
            if import_match:
                output_lines.append(f"    import {import_match.group(1)} <{line_no}>")
                continue

        if column == 0:
            variable_match = _PY_MODULE_VAR_RE.match(content)
            if variable_match:
                output_lines.append(f"    {variable_match.group(1)} = ... <{line_no}>")
                continue

    return "\n".join(output_lines)


def _md_outline_text(lines: list[str]) -> str:
    """从 Markdown 行列表中提取标题大纲。"""
    output_lines = ["行尾的尖括号表示行号"]
    for line_no, raw_line in enumerate(lines, start=1):
        match = HEADING_RE.match(raw_line.rstrip("\n\r"))
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        output_lines.append("\t" * (level - 1) + f"{title} <{line_no}>")
    return "\n".join(output_lines)
