"""对 .egent 运行 pylint 并返回诊断报告。"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import typing

import tools._output_util as output_util

_DEFAULT_PATHS = ("builtin/agent", "builtin/tools")
_EGENT_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PYLINTRC = _EGENT_ROOT / "pylintrc"
_DEFAULT_TIMEOUT_SECONDS = 120


def run_pylint(
    agent_client: typing.Any,
    paths: str | None = None,
    timeout: int | None = None,
) -> str:
    """对 .egent 目录运行 pylint，返回文本诊断报告。用于修改 .egent 代码后自查 lint 问题。

    @param paths: 要检查的路径（相对 .egent），多个用逗号分隔，缺省 `builtin/agent,builtin/tools`
    @param timeout: 超时秒数，缺省 120
    """
    del agent_client

    targets = _resolve_targets(paths)
    if isinstance(targets, str):
        return targets

    timeout_seconds = timeout if timeout is not None else _DEFAULT_TIMEOUT_SECONDS
    if timeout_seconds <= 0:
        return "错误：timeout 必须为正整数。"

    if not _PYLINTRC.is_file():
        return f"错误：未找到 pylint 配置：{_PYLINTRC}"

    command = [
        sys.executable,
        "-m",
        "pylint",
        *targets,
        f"--rcfile={_PYLINTRC}",
        "--output-format=text",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=_EGENT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except subprocess.TimeoutExpired:
        return f"错误：pylint 执行超时（{timeout_seconds} 秒）"
    except FileNotFoundError as error:
        return f"错误：无法启动 Python：{error}"

    if "No module named pylint" in result.stderr:
        return "错误：未安装 pylint。请执行：pip install pylint"

    output = result.stdout.strip()
    if result.stderr.strip():
        stderr_text = result.stderr.strip()
        output = f"{output}\n{stderr_text}".strip() if output else stderr_text

    if not output:
        checked = ", ".join(targets)
        if result.returncode == 0:
            return f"pylint 未发现任何问题（检查范围：{checked}）"
        return f"pylint 退出码 {result.returncode}，但未产生输出（检查范围：{checked}）"

    header = f"检查范围：{', '.join(targets)}（.egent）\n"
    if result.returncode != 0:
        header += f"退出码：{result.returncode}\n"
    return output_util.truncate_output(f"{header}\n{output}")


def _resolve_targets(paths: str | None) -> tuple[str, ...] | str:
    if not paths or not paths.strip():
        return _DEFAULT_PATHS

    targets: list[str] = []
    for segment in paths.split(","):
        relative_path = segment.strip().replace("\\", "/")
        if not relative_path:
            continue
        if relative_path.startswith("/") or ":" in relative_path[:3]:
            return f"错误：paths 必须是相对 .egent 的路径：{segment!r}"
        absolute_path = (_EGENT_ROOT / relative_path).resolve()
        try:
            absolute_path.relative_to(_EGENT_ROOT.resolve())
        except ValueError:
            return f"错误：路径必须在 .egent 内：{segment!r}"
        if not absolute_path.exists():
            return f"错误：路径不存在：{relative_path}"
        targets.append(relative_path)

    if not targets:
        return "错误：paths 不能为空。"
    return tuple(targets)
