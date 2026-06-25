"""项目内文本文件读取工具。"""

from __future__ import annotations

import pathlib
import re
import typing

import agent.tools._cs_outline
import agent.tools._output_util
import agent.tools._path_util

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "read_file_tool_read_file_outline_cs": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_file_outline_cs",
            "description": "读取 C# 源文件大纲（namespace / 类型 / 成员）。阅读 .cs 文件时先读大纲",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "C# 源文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    "read_file_tool_read_file_outline_md": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_file_outline_md",
            "description": "读取 Markdown 文件标题大纲。阅读 .md 文件时先读大纲",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Markdown 文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    "read_file_tool_read_lines": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_lines",
            "description": "按行号范围读取文件片段（1-based，含首尾）。通常在 grep_search 或大纲取得行号后使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对工作目录）",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "起始行号（1-based，含）",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "结束行号（1-based，含）",
                    },
                },
                "required": ["file_path", "start_line", "end_line"],
            },
        },
    },
    "read_file_tool_read_whole_file": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_whole_file",
            "description": "读取文件全文。用于非 .cs/.md 文件，或大纲策略无法定位细节时的 fallback",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class ReadFileTool:
    """读取工作区内文本文件。"""

    @staticmethod
    def read_file_outline_cs(file_path: str) -> str:
        """解析 C# 源文件大纲。"""
        absolute_path, resolve_error = ReadFileTool.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error

        warning = ""
        if absolute_path.suffix.lower() != ".cs":
            warning = f"警告：文件扩展名不是 .cs：{file_path}\n"

        try:
            lines = absolute_path.read_text(encoding="utf-8").splitlines(keepends=True)
        except OSError as error:
            return f"错误：无法读取文件：{error}"

        return warning + agent.tools._cs_outline.outline_cs_text(lines)

    @staticmethod
    def read_file_outline_md(file_path: str) -> str:
        """解析 Markdown 标题大纲。"""
        absolute_path, resolve_error = ReadFileTool.__resolve_file(file_path)
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

    @staticmethod
    def read_lines(file_path: str, start_line: int, end_line: int) -> str:
        """按行号范围读取文件片段（1-based，含首尾）。"""
        absolute_path, resolve_error = ReadFileTool.__resolve_file(file_path)
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
        return agent.tools._output_util.truncate_output(content)

    @staticmethod
    def read_whole_file(file_path: str) -> str:
        """读取文件全文。"""
        absolute_path, resolve_error = ReadFileTool.__resolve_file(file_path)
        if resolve_error is not None:
            return resolve_error
        try:
            content = absolute_path.read_text(encoding="utf-8")
        except OSError as error:
            return f"错误：无法读取文件：{error}"
        return agent.tools._output_util.truncate_output(content)

    @staticmethod
    def __resolve_file(file_path: str) -> tuple[pathlib.Path | None, str | None]:
        relative_path, path_error = agent.tools._path_util.resolve_relative_path(
            file_path,
            label="文件路径",
        )
        if path_error is not None:
            return None, path_error
        absolute_path = (pathlib.Path.cwd() / relative_path).resolve()
        if not absolute_path.is_file():
            return None, f"错误：文件不存在：{file_path}"
        return absolute_path, None
