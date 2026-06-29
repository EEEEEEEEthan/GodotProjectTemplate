"""Git 工具集：diff / add / commit。"""

from __future__ import annotations

import os
import re
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


def git_add(
    agent_client: typing.Any,
    *,
    paths: str = ".",
) -> str:
    """执行 git add 暂存文件变更。

    @param paths: 要添加的文件/目录路径，多个用逗号或空格分隔，缺省 "." 暂存所有变更
    """
    del agent_client

    # 解析 paths：支持逗号或空格分隔
    raw_paths = re.split(r"[,\s]+", paths.strip()) if paths.strip() else ["."]

    resolved_list: list[str] = []
    for raw in raw_paths:
        if not raw:
            continue
        resolved, error = path_util.resolve_relative_path(raw, label="git add 路径")
        if error is not None:
            return error
        resolved_list.append(os.fspath(resolved))

    if not resolved_list:
        return "错误：没有有效的路径"

    cmd = ["git", "add", "--", *resolved_list]

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
        return f"错误：执行 git add 失败：{error}"

    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout.strip())
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr.strip()}")

    output = "\n\n".join(parts) if parts else "(已暂存)"
    output = output_util.truncate_output(output)

    if result.returncode != 0:
        output += f"\n\n[exit code: {result.returncode}]"

    return output


def git_commit(
    agent_client: typing.Any,
    *,
    message: str,
) -> str:
    """执行 git commit 提交暂存区变更。

    @param message: 提交信息（必填）
    """
    del agent_client

    if not message or not message.strip():
        return "错误：提交信息不能为空"

    cmd = ["git", "commit", "-m", message.strip()]

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
        return f"错误：执行 git commit 失败：{error}"

    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout.strip())
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr.strip()}")

    output = "\n\n".join(parts) if parts else "(已提交)"
    output = output_util.truncate_output(output)

    if result.returncode != 0:
        output += f"\n\n[exit code: {result.returncode}]"

    return output
