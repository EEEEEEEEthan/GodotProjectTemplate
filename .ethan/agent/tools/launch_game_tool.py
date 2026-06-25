"""启动本地 Godot 游戏进程。"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import typing
from datetime import datetime

_ENGINE_RELATIVE = pathlib.Path(".engine") / ".engine.exe"
_PREPARE_BAT = pathlib.Path(".engine-prepare.bat")
_LAUNCH_LOG_DIRECTORY = pathlib.Path(".ethan") / ".temp"

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "launch_game_tool_launch_game": {
        "type": "function",
        "function": {
            "name": "launch_game_tool_launch_game",
            "description": (
                "启动 Godot 游戏。会输出端口号，可以用mcp连接游戏。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "headless": {
                        "type": "boolean",
                        "description": "是否以无头模式启动，缺省 false（窗口模式）",
                    },
                    "skip_prepare": {
                        "type": "boolean",
                        "description": "是否跳过 .engine-prepare.bat，缺省 false",
                    },
                    "skip_import": {
                        "type": "boolean",
                        "description": "是否跳过 --headless --import 资源导入，缺省 false",
                    },
                    "extra_arguments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "追加传给引擎的命令行参数",
                    },
                },
            },
        },
    },
}


class LaunchGameTool:
    """使用 .engine/.engine.exe 启动 Godot 游戏。"""

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
            prepare_error = LaunchGameTool.__run_prepare(project_root, prepare_script)
            if prepare_error is not None:
                return prepare_error

        if not engine_executable.is_file():
            return (
                f"错误：引擎不存在：{_ENGINE_RELATIVE.as_posix()}。"
                "请先运行 .engine-prepare.bat 或去掉 skip_prepare。"
            )

        if not skip_import:
            import_error = LaunchGameTool.__run_import(project_root, engine_executable)
            if import_error is not None:
                return import_error

        launch_arguments = list(extra_arguments) if extra_arguments else []
        if headless:
            launch_arguments = ["--headless", *launch_arguments]

        log_path = LaunchGameTool.__create_launch_log_path(project_root)
        relative_log_path = log_path.relative_to(project_root).as_posix()
        launch_arguments = ["--log-file", relative_log_path, *launch_arguments]

        process_error = LaunchGameTool.__start_detached_process(
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
            f"额外日志：{relative_log_path}\n"
            "请在上述日志或游戏控制台中查找「Game MCP: HTTP 服务已启动，端口 XXXX」，"
            "再使用 MCP game_command 连接。"
        )

    @staticmethod
    def __run_prepare(
        project_root: pathlib.Path,
        prepare_script: pathlib.Path,
    ) -> str | None:
        if not prepare_script.is_file():
            return f"错误：未找到 {prepare_script.name}。"
        completed = LaunchGameTool.__run_synchronous(
            ["cmd.exe", "/c", str(prepare_script)],
            project_root=project_root,
        )
        if isinstance(completed, str):
            return completed
        if completed.returncode != 0:
            return LaunchGameTool.__format_process_failure(
                "引擎准备失败",
                completed,
            )
        return None

    @staticmethod
    def __run_import(
        project_root: pathlib.Path,
        engine_executable: pathlib.Path,
    ) -> str | None:
        completed = LaunchGameTool.__run_synchronous(
            [str(engine_executable), "--headless", "--import"],
            project_root=project_root,
        )
        if isinstance(completed, str):
            return completed
        if completed.returncode != 0:
            return LaunchGameTool.__format_process_failure(
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
            )
        except OSError as error:
            return f"错误：无法启动游戏进程：{error}"
        return None

    @staticmethod
    def __create_launch_log_path(project_root: pathlib.Path) -> pathlib.Path:
        log_directory = project_root / _LAUNCH_LOG_DIRECTORY
        log_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return log_directory / f"game_{timestamp}.log"

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
