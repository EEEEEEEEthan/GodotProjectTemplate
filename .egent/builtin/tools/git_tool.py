"""Git 差异工具。"""

from __future__ import annotations

import os
import subprocess
import typing

from . import _output_util as output_util
from . import _path_util as path_util


def git_diff(
    agent_client: typing.Any,
    *,
    staged: bool = False,
    stat: bool = False,
    name_only: bool = False,
    file_path: str | None = None,
) -> str:
    """执行 git diff 查看工作区变更。

    @param staged: 是否查看暂存区变更（--staged）
    @param stat: 是否仅显示统计摘要（--stat）
    @param name_only: 是否仅显示文件名（--name-only）
    @param file_path: 限定文件路径（相对工作目录）
    """
    del agent_client

    cmd = ["git", "diff"]

    if staged:
        cmd.append("--staged")
    if stat:
        cmd.append("--stat")
    if name_only:
        cmd.append("--name-only")

    if file_path is not None:
        resolved, error = path_util.resolve_relative_path(
            file_path,
            label="file_path",
        )
        if error is not None:
            return error
        cmd.append("--")
        cmd.append(os.fspath(resolved))

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            check=False,
        )
    except FileNotFoundError:
        return "错误：未找到 git 命令，请确认 git 已安装并在 PATH 中。"
    except OSError as error:
        return f"错误：执行 git diff 失败：{error}"

    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout.strip())
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr.strip()}")

    output = "\n\n".join(parts) if parts else "(无差异)"
    output = output_util.truncate_output(output)

    if result.returncode != 0:
        output += f"\n\n[exit code: {result.returncode}]"

    return output
