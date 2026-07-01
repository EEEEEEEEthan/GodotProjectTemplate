"""启动本地 Godot 游戏进程。"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime

import agent.data_loader
import agent.tool_binding

_MCP_READY_LOG_PATTERN = re.compile(
    r"<<<EGENT::GAME_MCP::HANDSHAKE::v1::port=(\d+)>>>"
)
_MCP_BIND_FAILED_MARKER = "<<<EGENT::GAME_MCP::HANDSHAKE::v1::BIND_FAILED>>>"
_MCP_READY_POLL_INTERVAL_SECONDS = 0.2
_MCP_READY_POLL_TIMEOUT_SECONDS = 3.0
_MCP_PROCESS_TERMINATE_TIMEOUT_SECONDS = 3.0

_ENGINE_RELATIVE = pathlib.Path(".engine") / ".engine.exe"
_PREPARE_BAT = pathlib.Path(".engine-prepare.bat")


@agent.tool_binding.agent_tool(readonly=True)
def launch_game(
    *,
    headless: bool = False,
    skip_prepare: bool = False,
    skip_import: bool = False,
    extra_arguments: list[str] | None = None,
) -> str:
    """启动 Godot 游戏。会输出端口号，可以用 MCP 连接游戏。

    @param headless: 是否以无头模式启动，缺省 false（窗口模式）
    @param skip_prepare: 是否跳过 .engine-prepare.bat，缺省 false
    @param skip_import: 是否跳过 --headless --import 资源导入，缺省 false
    @param extra_arguments: 追加传给引擎的命令行参数
    """
    project_root = agent.data_loader.PROJECT_ROOT
    engine_executable = (project_root / _ENGINE_RELATIVE).resolve()
    prepare_script = (project_root / _PREPARE_BAT).resolve()

    if not skip_prepare:
        prepare_error = _run_prepare(project_root, prepare_script)
        if prepare_error is not None:
            return prepare_error

    if not engine_executable.is_file():
        return (
            f"错误：引擎不存在：{_ENGINE_RELATIVE.as_posix()}。"
            "请先运行 .engine-prepare.bat 或去掉 skip_prepare。"
        )

    if not skip_import:
        import_error = _run_import(project_root, engine_executable)
        if import_error is not None:
            return import_error

    launch_arguments = list(extra_arguments) if extra_arguments else []
    if headless:
        launch_arguments = ["--headless", *launch_arguments]

    log_path = _create_launch_log_path(project_root)
    relative_log_path = log_path.relative_to(project_root).as_posix()
    launch_arguments = ["--log-file", relative_log_path, *launch_arguments]

    process = _start_detached_process(
        project_root,
        engine_executable,
        launch_arguments,
    )
    if isinstance(process, str):
        return process

    port_result = _wait_for_mcp_port(log_path, process)
    if isinstance(port_result, str):
        return port_result

    mode_label = "无头模式" if headless else "窗口模式"
    return (
        f"游戏已启动（{mode_label}）。\n"
        f"MCP 端口：{port_result}\n"
        f"日志：{relative_log_path}\n"
        "可使用 MCP game_command 连接。"
    )


def _run_prepare(
    project_root: pathlib.Path,
    prepare_script: pathlib.Path,
) -> str | None:
    if not prepare_script.is_file():
        return f"错误：未找到 {prepare_script.name}。"
    completed = _run_synchronous(
        ["cmd.exe", "/c", str(prepare_script)],
        project_root=project_root,
    )
    if isinstance(completed, str):
        return completed
    if completed.returncode != 0:
        return _format_process_failure(
            "引擎准备失败",
            completed,
        )
    return None


def _run_import(
    project_root: pathlib.Path,
    engine_executable: pathlib.Path,
) -> str | None:
    completed = _run_synchronous(
        [str(engine_executable), "--headless", "--import"],
        project_root=project_root,
    )
    if isinstance(completed, str):
        return completed
    if completed.returncode != 0:
        return _format_process_failure(
            "资源导入失败",
            completed,
        )
    return None


def _start_detached_process(
    project_root: pathlib.Path,
    engine_executable: pathlib.Path,
    launch_arguments: list[str],
) -> subprocess.Popen[bytes] | str:
    command = [str(engine_executable), *launch_arguments]
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = (
            subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
    try:
        return subprocess.Popen(
            command,
            cwd=os.fspath(project_root),
            creationflags=creation_flags,
            close_fds=True,
        )
    except OSError as error:
        return f"错误：无法启动游戏进程：{error}"


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        process.terminate()
        try:
            process.wait(timeout=_MCP_PROCESS_TERMINATE_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    except OSError:
        pass


def _read_log_tail(log_path: pathlib.Path, *, max_lines: int = 20) -> str:
    if not log_path.is_file():
        return ""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    if not lines:
        return ""
    tail = "\n".join(lines[-max_lines:])
    return f"--- 日志末尾 ---\n{tail}"


def _wait_for_mcp_port(
    log_path: pathlib.Path,
    process: subprocess.Popen[bytes],
) -> int | str:
    deadline = time.monotonic() + _MCP_READY_POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if log_path.is_file():
            try:
                content = log_path.read_text(encoding="utf-8", errors="replace")
            except OSError as error:
                return f"错误：无法读取启动日志（{log_path.as_posix()}）：{error}"
            if _MCP_BIND_FAILED_MARKER in content:
                _terminate_process(process)
                return (
                    f"错误：游戏 MCP 无法绑定端口（{log_path.as_posix()}）。\n"
                    f"{_read_log_tail(log_path)}"
                )
            match = _MCP_READY_LOG_PATTERN.search(content)
            if match:
                return int(match.group(1))
        time.sleep(_MCP_READY_POLL_INTERVAL_SECONDS)
    _terminate_process(process)
    return (
        f"错误：{int(_MCP_READY_POLL_TIMEOUT_SECONDS)} 秒内未在日志中找到 MCP 握手标记，"
        f"已终止游戏进程（{log_path.as_posix()}）。\n"
        f"{_read_log_tail(log_path)}"
    )


def _create_launch_log_path(project_root: pathlib.Path) -> pathlib.Path:
    del project_root
    log_directory = agent.data_loader.EGENT_TEMP_DIR
    log_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return log_directory / f"game_{timestamp}.log"


def _run_synchronous(
    command: list[str],
    *,
    project_root: pathlib.Path,
) -> subprocess.CompletedProcess[str] | str:
    try:
        return subprocess.run(
            command,
            cwd=os.fspath(project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as error:
        return f"错误：无法执行命令：{error}"


def _format_process_failure(
    title: str,
    completed: subprocess.CompletedProcess[str],
) -> str:
    parts = [f"错误：{title}（退出码 {completed.returncode}）"]
    if completed.stdout.strip():
        parts.extend(["--- stdout ---", completed.stdout.strip()])
    if completed.stderr.strip():
        parts.extend(["--- stderr ---", completed.stderr.strip()])
    return "\n".join(parts)
