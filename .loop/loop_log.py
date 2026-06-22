"""Dev Loop 会话日志：写入 .loop/.logs/。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from config import LOOP_LOGS_DIR


def _format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _serialize(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except TypeError:
        return repr(value)


class LoopRunLogger:
    @classmethod
    def open(cls, logs_directory: Path = LOOP_LOGS_DIR) -> LoopRunLogger:
        logs_directory.mkdir(parents=True, exist_ok=True)
        log_filename = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
        return cls(logs_directory / log_filename)

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._file = log_path.open("a", encoding="utf-8")
        self._round_section: str | None = None
        self._write_file_header()

    def _write_file_header(self) -> None:
        self._file.write("# Dev Loop 会话日志\n")
        self._file.write(f"# 文件: {self.log_path.name}\n")
        self._file.write(f"# 开始: {_format_timestamp()}\n\n")
        self._file.flush()

    def log_banner(self, text: str) -> None:
        self._finish_agent_round()
        self._file.write(f"{'=' * 72}\n[banner] {_format_timestamp()}\n{text}\n")
        self._file.flush()

    def log_user(self, text: str) -> None:
        self._finish_agent_round()
        self._file.write(f"{'=' * 72}\n[你] {_format_timestamp()}\n{text}\n")
        self._file.flush()

    def log_role(self, tag: str, text: str) -> None:
        self._finish_agent_round()
        self._file.write(f"\n[{tag}] {_format_timestamp()}\n{text}\n")
        self._file.flush()

    def begin_agent_round(self, role_tag: str, prompt: str) -> None:
        self._finish_agent_round()
        self._file.write(
            f"{'=' * 72}\n[{role_tag}] prompt {_format_timestamp()}\n{prompt}\n"
        )
        self._round_section = None
        self._file.flush()

    def append_thinking(self, text: str) -> None:
        if not text:
            return
        self._ensure_round_section("thinking")
        self._file.write(text)
        self._file.flush()

    def append_assistant(self, text: str) -> None:
        if not text:
            return
        self._ensure_round_section("assistant")
        self._file.write(text)
        self._file.flush()

    def log_tool_call_message(self, message: object) -> None:
        self._close_round_section()
        tool_name = str(getattr(message, "name", "") or "")
        tool_status = str(getattr(message, "status", "") or "")
        tool_args = getattr(message, "args", None)
        tool_result = getattr(message, "result", None)
        self._file.write(f"\n[tool_call] {tool_name} ({tool_status})\n")
        if tool_args is not None:
            self._file.write(f"args:\n{_serialize(tool_args)}\n")
        if tool_result is not None:
            self._file.write(f"result:\n{_serialize(tool_result)}\n")
        self._file.flush()

    def log_interaction_tool_update(self, update_type: str, update: object) -> None:
        self._close_round_section()
        tool_call = (
            update.get("toolCall")
            if isinstance(update, dict)
            else getattr(update, "tool_call", None)
        )
        if not isinstance(tool_call, dict):
            tool_call = {}
        self._file.write(f"\n[{update_type}]\n{_serialize(tool_call)}\n")
        self._file.flush()

    def finish_agent_round(self) -> None:
        self._finish_agent_round()
        self._file.write("\n")
        self._file.flush()

    def _ensure_round_section(self, section: str) -> None:
        if self._round_section == section:
            return
        self._close_round_section()
        self._file.write(f"\n[{section}]\n")
        self._round_section = section
        self._file.flush()

    def _close_round_section(self) -> None:
        if self._round_section is not None:
            self._file.write("\n")
            self._round_section = None

    def _finish_agent_round(self) -> None:
        self._close_round_section()

    def close(self) -> None:
        self._finish_agent_round()
        self._file.write(f"\n# 结束: {_format_timestamp()}\n")
        self._file.close()

    def __enter__(self) -> LoopRunLogger:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
