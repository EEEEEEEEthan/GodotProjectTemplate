"""向运行中 Godot 游戏 MCP HTTP 服务发送协议命令，并启动游戏进程。"""

from __future__ import annotations

import importlib
import json
import os
import pathlib
import subprocess
import sys
import typing

_game_client = importlib.import_module("agent.tools._game_client")
_output_util = importlib.import_module("agent.tools._output_util")

_ENGINE_RELATIVE = pathlib.Path(".engine") / ".engine.exe"
_PREPARE_BAT = pathlib.Path(".engine-prepare.bat")


class GameCommandTool:
    """连接游戏 HTTP 服务、发送已注册协议，并启动本地 Godot 实例。"""

    @staticmethod
    def launch_game(
        *,
        headless: bool = False,
        skip_prepare: bool = False,
        skip_import: bool = False,
        extra_arguments: list[str] | None = None,
    ) -> str:
        """使用 .engine/.engine.exe 启动 Godot 游戏（后台进程）。"""
        project_root = pathlib.Path.cwd()
        engine_executable = (project_root / _ENGINE_RELATIVE).resolve()
        prepare_script = (project_root / _PREPARE_BAT).resolve()

        if not skip_prepare:
            prepare_error = GameCommandTool.__run_prepare(project_root, prepare_script)
            if prepare_error is not None:
                return prepare_error

        if not engine_executable.is_file():
            return (
                f"错误：引擎不存在：{_ENGINE_RELATIVE.as_posix()}。"
                "请先运行 .engine-prepare.bat 或去掉 skip_prepare。"
            )

        if not skip_import:
            import_error = GameCommandTool.__run_import(project_root, engine_executable)
            if import_error is not None:
                return import_error

        launch_arguments = list(extra_arguments) if extra_arguments else []
        if headless:
            launch_arguments = ["--headless", *launch_arguments]

        process_error = GameCommandTool.__start_detached_process(
            project_root,
            engine_executable,
            launch_arguments,
        )
        if process_error is not None:
            return process_error

        mode_label = "无头模式" if headless else "窗口模式"
        return (
            f"游戏已启动（{mode_label}）。\n"
            f"引擎：{_ENGINE_RELATIVE.as_posix()}\n"
            f"工作目录：{project_root}\n"
            "请在游戏控制台日志中查找「Game MCP: HTTP 服务已启动，端口 XXXX」，"
            "再使用 game_command_tool_send_command 连接。"
        )

    @staticmethod
    def send_command(
        command: str,
        data: dict[str, typing.Any] | None = None,
        *,
        port: int | None = None,
        host: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        """向游戏 MCP 服务发送协议并返回 JSON 结果。"""
        if not command or not command.strip():
            return "错误：command 不能为空。"
        resolved_port = (
            port
            if port is not None
            else _game_client.DEFAULT_PORT
        )
        if resolved_port <= 0:
            return "错误：port 必须是正整数。"
        resolved_host = (host or _game_client.DEFAULT_HOST).strip()

        try:
            result = _game_client.send_command(
                resolved_port,
                command.strip(),
                data,
                host=resolved_host or _game_client.DEFAULT_HOST,
                timeout_seconds=timeout_seconds,
            )
        except _game_client.GameCommandError as error:
            return f"错误：{error}"

        formatted = json.dumps(result, ensure_ascii=False, indent=2)
        return _output_util.truncate_output(formatted)

    @staticmethod
    def __run_prepare(
        project_root: pathlib.Path,
        prepare_script: pathlib.Path,
    ) -> str | None:
        if not prepare_script.is_file():
            return f"错误：未找到 {prepare_script.name}。"
        completed = GameCommandTool.__run_synchronous(
            ["cmd.exe", "/c", str(prepare_script)],
            project_root=project_root,
        )
        if isinstance(completed, str):
            return completed
        if completed.returncode != 0:
            return GameCommandTool.__format_process_failure(
                "引擎准备失败",
                completed,
            )
        return None

    @staticmethod
    def __run_import(
        project_root: pathlib.Path,
        engine_executable: pathlib.Path,
    ) -> str | None:
        completed = GameCommandTool.__run_synchronous(
            [str(engine_executable), "--headless", "--import"],
            project_root=project_root,
        )
        if isinstance(completed, str):
            return completed
        if completed.returncode != 0:
            return GameCommandTool.__format_process_failure(
                "资源导入失败",
                completed,
            )
        return None

    @staticmethod
    def __start_detached_process(
        project_root: pathlib.Path,
        engine_executable: pathlib.Path,
        launch_arguments: list[str],
    ) -> str | None:
        command = [str(engine_executable), *launch_arguments]
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = (
                subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            )
        try:
            subprocess.Popen(
                command,
                cwd=os.fspath(project_root),
                creationflags=creation_flags,
                close_fds=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as error:
            return f"错误：无法启动游戏进程：{error}"
        return None

    @staticmethod
    def __run_synchronous(
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
            )
        except OSError as error:
            return f"错误：无法执行命令：{error}"

    @staticmethod
    def __format_process_failure(
        title: str,
        completed: subprocess.CompletedProcess[str],
    ) -> str:
        parts = [f"错误：{title}（退出码 {completed.returncode}）"]
        if completed.stdout.strip():
            parts.extend(["--- stdout ---", completed.stdout.strip()])
        if completed.stderr.strip():
            parts.extend(["--- stderr ---", completed.stderr.strip()])
        return "\n".join(parts)
