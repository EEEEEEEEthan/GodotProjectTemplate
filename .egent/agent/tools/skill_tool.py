"""Skill 工具：加载 skill 文档并执行 skill 脚本。"""

from __future__ import annotations

import asyncio
import os
import subprocess
import typing
import uuid

import pathlib

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "skill_tool_learn_skill": {
        "type": "function",
        "function": {
            "name": "skill_tool_learn_skill",
            "description": "读取技能",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "技能id，与系统消息中列表一致",
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "相对技能根目录的文件路径，缺省表示 SKILL.md",
                    },
                },
                "required": ["skill_id"],
            },
        },
    },
    "skill_tool_run_skill_script": {
        "type": "function",
        "function": {
            "name": "skill_tool_run_skill_script",
            "description": "在 Agent 当前工作目录下执行技能包内脚本，标准输出与标准错误合并返回。使用脚本前请使用learn_skill工具阅读技能文档",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "技能 id，与系统消息中列表一致",
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "相对技能根目录的脚本文件路径",
                    },
                    "script_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选：按顺序传给脚本的命令行参数",
                    },
                },
                "required": ["skill_id", "relative_path"],
            },
        },
    },
}

class SkillTool:
    """读取 skill 文档并执行 skill 包内脚本。"""

    def __init__(
        self,
        agent: typing.Any,
    ) -> None:
        self.__skill_index = agent.skill_index
        self.__agent_name = agent.name

    def learn_skill(
        self,
        skill_id: str,
        relative_path: str | None = None,
    ) -> str:
        """读取 skill 文档，默认返回目录结构 + SKILL.md。"""
        if not skill_id or not skill_id.strip():
            return "错误：skill_id 不能为空。"

        summary = self.__skill_index.get(skill_id.strip())
        if summary is None:
            return f"错误：未找到技能 id「{skill_id}」。请使用系统消息中列出的 id。"

        skill_root = pathlib.Path(summary[2]).resolve()
        use_implicit_default = not relative_path or not relative_path.strip()
        relative_segment = (
            "SKILL.md"
            if use_implicit_default
            else relative_path.strip().lstrip("/\\")
        )
        if not relative_segment:
            relative_segment = "SKILL.md"

        absolute_file, resolve_error, _ = self.__resolve_under_root(skill_root, relative_segment)
        if resolve_error is not None:
            return resolve_error

        try:
            file_text = absolute_file.read_text(encoding="utf-8")
        except OSError as exception:
            return f"错误：无法读取文件：{exception}"

        if not use_implicit_default:
            return file_text

        if not skill_root.is_dir():
            listing = "(无法列出：根目录不存在)"
        else:
            try:
                lines = sorted(
                    (
                        str(path.relative_to(skill_root))
                        for path in skill_root.rglob("*")
                        if not self.__is_internal_skill_path(str(path.relative_to(skill_root)))
                    ),
                    key=str.casefold,
                )
            except OSError as exception:
                listing = f"(列出失败：{exception})"
            else:
                listing = "(空目录)" if not lines else "\n".join(lines)
        return (
            "### 技能目录结构（相对技能根目录）\n"
            f"{listing}\n"
            f"### {relative_segment} 全文\n"
            f"{file_text}\n"
        )

    async def run_skill_script(
        self,
        skill_id: str,
        relative_path: str | None = None,
        script_args: list[str] | None = None,
    ) -> str:
        """在 agent 工作目录下执行 skill 脚本并返回输出。"""
        absolute_script, error = self.__resolve_script_for_run(skill_id, relative_path)
        if error is not None:
            return error

        command = self.__build_script_command(
            absolute_script,
            self.__agent_name,
            script_args,
        )
        if isinstance(command, str):
            return command

        completed = await self.__invoke_script(command)
        if isinstance(completed, str):
            return completed

        result = self.__format_process_output(completed)
        if len(result) <= 10_000:
            return result
        return self.__persist_oversized_output(result)

    def __resolve_script_for_run(
        self,
        skill_id: str,
        relative_path: str | None,
    ) -> tuple[pathlib.Path | None, str | None]:
        absolute_script: pathlib.Path | None = None
        error: str | None = None

        if not skill_id or not skill_id.strip():
            error = "错误：skill_id 不能为空。"
        elif not relative_path or not relative_path.strip():
            error = "错误：relative_path 不能为空。"
        else:
            trimmed_skill_id = skill_id.strip()
            summary = self.__skill_index.get(trimmed_skill_id)
            if summary is None:
                error = f"错误：未找到技能 id「{skill_id}」。请使用系统消息中列出的 id。"
            else:
                skill_root = pathlib.Path(summary[2]).resolve()
                relative_segment = relative_path.strip().lstrip("/\\")
                if not relative_segment:
                    error = "错误：relative_path 无效。"
                elif self.__is_internal_skill_path(relative_segment):
                    error = (
                        "错误：下划线开头的路径为技能内部文件，"
                        "不可通过 run_skill_script 执行。"
                    )
                else:
                    script, resolve_error, file_missing = self.__resolve_under_root(
                        skill_root,
                        relative_segment,
                        allow_missing=True,
                    )
                    if resolve_error is None:
                        absolute_script = script
                    elif file_missing:
                        error = "\n".join(
                            [
                                f"脚本不存在：{relative_segment}",
                                "",
                                self.learn_skill(trimmed_skill_id),
                            ]
                        )
                    else:
                        error = resolve_error

        return absolute_script, error

    @staticmethod
    def __build_script_command(
        absolute_script: pathlib.Path,
        agent_name: str,
        script_args: list[str] | None,
    ) -> list[str] | str:
        tail_arguments = list(script_args) if script_args else []
        extension = absolute_script.suffix.lower()
        script_text = str(absolute_script)
        launch_arguments = [*tail_arguments, "--agent-name", agent_name]
        if extension == ".ps1":
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                script_text,
                *launch_arguments,
            ]
        elif extension in {".cmd", ".bat"}:
            command = ["cmd.exe", "/c", script_text, *launch_arguments]
        elif extension == ".py":
            command = ["python", script_text, *launch_arguments]
        elif extension == ".js":
            command = ["node", script_text, *launch_arguments]
        elif extension == ".sh":
            command = ["bash", script_text, *launch_arguments]
        elif extension == ".exe":
            command = [script_text, *launch_arguments]
        else:
            supported = ".ps1 .bat .cmd .py .js .sh .exe"
            return f"错误：不支持的脚本扩展名「{extension}」。支持：{supported}"
        return command

    async def __invoke_script(
        self,
        command: list[str],
    ) -> subprocess.CompletedProcess[str] | str:
        try:
            environment = os.environ.copy()
            working_directory = os.getcwd()
            existing_pythonpath = environment.get("PYTHONPATH", "")
            environment["PYTHONPATH"] = (
                working_directory
                if not existing_pythonpath
                else f"{working_directory}{os.pathsep}{existing_pythonpath}"
            )
            return await asyncio.wait_for(
                asyncio.to_thread(
                    subprocess.run,
                    command,
                    cwd=working_directory,
                    env=environment,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                ),
                timeout=300,
            )
        except TimeoutError:
            return "错误：脚本执行超过 5 分钟已终止。"
        except OSError as exception:
            return f"错误：无法启动进程：{exception}"

    @staticmethod
    def __format_process_output(completed: subprocess.CompletedProcess[str]) -> str:
        builder = [f"退出码：{completed.returncode}"]
        if completed.stdout:
            builder.extend(["--- stdout ---", completed.stdout])
        if completed.stderr:
            builder.extend(["--- stderr ---", completed.stderr])
        return "\n".join(builder)

    @staticmethod
    def __persist_oversized_output(result: str) -> str:
        guid = str(uuid.uuid4())
        relative_output = f".egent/.temp/{guid}.txt"
        output_dir = pathlib.Path.cwd() / ".egent" / ".temp"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / f"{guid}.txt").write_text(result, encoding="utf-8")
        return (
            f"输出结果太长,已保存到{relative_output}。\n\n"
            "grep_search_tool_grep_search 定向查询该文件：\n"
            f'pattern="关键词", directory=".egent/.temp", filter="{guid}.txt"\n\n'
            "read_file_tool_read_lines 按行号读片段：\n"
            f'file_path="{relative_output}", start_line=120, end_line=140\n'
        )

    @staticmethod
    def __is_internal_skill_path(relative_path: str) -> bool:
        for segment in pathlib.Path(relative_path).parts:
            if segment and segment[0] == "_":
                return True
        return False

    @staticmethod
    def __resolve_under_root(
        skill_root: pathlib.Path,
        relative_path: str,
        *,
        allow_missing: bool = False,
    ) -> tuple[pathlib.Path | None, str | None, bool]:
        combined = (skill_root / relative_path).resolve()
        root_with_separator = str(skill_root) + os.sep
        combined_text = str(combined)
        if not combined_text.startswith(root_with_separator) and combined_text != str(skill_root):
            return None, "错误：路径越界，必须位于技能根目录内。", False
        if combined.is_dir():
            return None, "错误：目标是目录而非文件。", False
        if not combined.is_file():
            if allow_missing:
                return combined, f"错误：文件不存在：{relative_path}", True
            return None, f"错误：文件不存在：{relative_path}", False
        return combined, None, False
