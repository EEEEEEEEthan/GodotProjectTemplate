"""本地 shell 命令执行工具 — 仅供 ethan 使用，权限极高。"""

from __future__ import annotations

import os
import subprocess
import typing

from . import _schema_util as schema_util
from . import _output_util as output_util

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "shell_tool_exec": schema_util.function_schema(
        "shell_tool_exec",
        "在本地系统执行任意 shell 命令（cmd /c）。"
        "权限极高，无沙箱限制。可执行文件操作、启动进程、查询系统状态等。"
        "输出超过 10000 字符会被截断。超时 5 分钟。",
        {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令，例如 'dir'、'echo hello'、'python script.py'",
            },
            "cwd": {
                "type": "string",
                "description": "工作目录，缺省为项目根目录",
            },
        },
        required=["command"],
    ),
}


class ShellTool:
    """执行本地 shell 命令并返回输出。"""

    @staticmethod
    def exec(command: str, cwd: str | None = None) -> str:
        """执行 shell 命令，返回 stdout+stderr 合并输出。"""
        if not command or not command.strip():
            return "错误：command 不能为空。"

        work_dir = cwd.strip() if cwd else None
        if work_dir:
            work_dir = os.path.abspath(work_dir)
            if not os.path.isdir(work_dir):
                return f"错误：目录不存在：{work_dir}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return "错误：命令执行超时（300 秒）"
        except FileNotFoundError as error:
            return f"错误：命令未找到：{error}"
        except PermissionError as error:
            return f"错误：权限不足：{error}"
        except OSError as error:
            return f"错误：系统调用失败：{error}"

        parts: list[str] = []
        if result.stdout:
            parts.append(result.stdout.strip())
        if result.stderr:
            parts.append(f"[stderr]\n{result.stderr.strip()}")

        output = "\n\n".join(parts) if parts else "(无输出)"
        output = output_util.truncate_output(output)

        if result.returncode != 0:
            output += f"\n\n[exit code: {result.returncode}]"

        return output
