"""Cursor SDK agent 会话封装。"""

import sys
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from cursor_sdk import Agent, AgentOptions, Client, CursorAgentError, LocalAgentOptions

from config import DEFAULT_MODEL, PROJECT_ROOT, SETTINGS_DIR, load_role_setting_sources
from plan_extract import extract_plan

if TYPE_CHECKING:
    from loop_log import LoopRunLogger

_CONSOLE_DIM = "\033[90m"
_CONSOLE_RESET = "\033[0m"
_WINDOWS_ANSI_ENABLED = False
_TOOL_INTERACTION_TYPES = frozenset(
    {"tool-call-started", "tool-call-completed", "partial-tool-call"}
)


def load_role_prompt(role_key: str) -> str:
    path = SETTINGS_DIR / f"{role_key}.txt"
    return path.read_text(encoding="utf-8")


def print_role(
    tag: str,
    text: str,
    *,
    run_logger: "LoopRunLogger | None" = None,
) -> None:
    print(f"\n[{tag}]\n{text}\n")
    if run_logger is not None:
        run_logger.log_role(tag, text)


def _enable_windows_ansi() -> None:
    global _WINDOWS_ANSI_ENABLED
    if _WINDOWS_ANSI_ENABLED or sys.platform != "win32":
        return
    try:
        import ctypes

        console_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        console_mode = ctypes.c_uint()
        ctypes.windll.kernel32.GetConsoleMode(
            console_handle, ctypes.byref(console_mode)
        )
        ctypes.windll.kernel32.SetConsoleMode(
            console_handle, console_mode.value | 0x0004
        )
        _WINDOWS_ANSI_ENABLED = True
    except Exception:
        _WINDOWS_ANSI_ENABLED = True


def _interaction_update_type(update: object) -> str:
    if isinstance(update, Mapping):
        return str(update.get("type") or "")
    return str(getattr(update, "type", "") or "")


def _interaction_update_text(update: object) -> str:
    if isinstance(update, Mapping):
        return str(update.get("text") or "")
    return str(getattr(update, "text", "") or "")


def _print_thinking(text: str, *, in_thinking: bool) -> bool:
    if not text:
        return in_thinking
    if not in_thinking:
        print(f"{_CONSOLE_DIM}", end="", flush=True)
    print(text, end="", flush=True)
    return True


def _end_thinking_line(in_thinking: bool) -> bool:
    if in_thinking:
        print(_CONSOLE_RESET, end="", flush=True)
        print(flush=True)
    return False


def stream_run(
    run,
    tag: str,
    *,
    run_logger: "LoopRunLogger | None" = None,
) -> None:
    _enable_windows_ansi()
    print(f"\n[{tag}] ", end="", flush=True)

    in_thinking = False
    thinking_delta_seen = False
    assistant_delta_seen = False

    for event in run.events():
        update = event.interaction_update
        if update is not None:
            update_type = _interaction_update_type(update)
            if update_type == "thinking-delta":
                thinking_delta_seen = True
                thinking_text = _interaction_update_text(update)
                in_thinking = _print_thinking(thinking_text, in_thinking=in_thinking)
                if run_logger is not None:
                    run_logger.append_thinking(thinking_text)
                continue
            if update_type == "thinking-completed":
                in_thinking = _end_thinking_line(in_thinking)
                continue
            if update_type == "text-delta":
                assistant_delta_seen = True
                in_thinking = _end_thinking_line(in_thinking)
                assistant_text = _interaction_update_text(update)
                if assistant_text:
                    print(assistant_text, end="", flush=True)
                    if run_logger is not None:
                        run_logger.append_assistant(assistant_text)
                continue
            if update_type in _TOOL_INTERACTION_TYPES and run_logger is not None:
                in_thinking = _end_thinking_line(in_thinking)
                run_logger.log_interaction_tool_update(update_type, update)
                continue

        message = event.sdk_message
        if message is None:
            continue

        message_type = getattr(message, "type", "")
        if message_type == "thinking":
            if thinking_delta_seen:
                continue
            thinking_text = getattr(message, "text", "")
            in_thinking = _print_thinking(thinking_text, in_thinking=in_thinking)
            if run_logger is not None:
                run_logger.append_thinking(thinking_text)
            continue

        if message_type == "tool_call":
            in_thinking = _end_thinking_line(in_thinking)
            if run_logger is not None:
                run_logger.log_tool_call_message(message)
            continue

        if message_type != "assistant":
            continue

        in_thinking = _end_thinking_line(in_thinking)
        if assistant_delta_seen:
            continue
        content = getattr(getattr(message, "message", None), "content", ())
        for block in content:
            text = getattr(block, "text", "")
            if text:
                print(text, end="", flush=True)
                if run_logger is not None:
                    run_logger.append_assistant(text)

    _end_thinking_line(in_thinking)
    print(flush=True)
    if run_logger is not None:
        run_logger.finish_agent_round()


class AgentSession:
    def __init__(
        self,
        role_key: str,
        system_prompt: str,
        *,
        client: Client,
        mode: str,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        cwd: Path = PROJECT_ROOT,
        console_tag: str | None = None,
        echo_plan: bool = False,
        run_logger: "LoopRunLogger | None" = None,
    ) -> None:
        self.role_key = role_key
        self.console_tag = console_tag or role_key
        self.system_prompt = system_prompt
        self._bootstrapped = False
        self._echo_plan = echo_plan
        self._run_logger = run_logger
        options = AgentOptions(
            api_key=api_key,
            model=model,
            mode=mode,
            local=LocalAgentOptions(
                cwd=str(cwd),
                setting_sources=load_role_setting_sources(role_key),
            ),
        )
        self._agent = Agent.create(options, client=client)

    @property
    def agent_id(self) -> str:
        return self._agent.agent_id

    def send(self, user_message: str, *, stream: bool = True) -> str:
        if not self._bootstrapped:
            prompt = f"{self.system_prompt}\n\n---\n\n{user_message}"
            self._bootstrapped = True
        else:
            prompt = user_message
        if self._run_logger is not None:
            self._run_logger.begin_agent_round(self.console_tag, prompt)
        try:
            run = self._agent.send(prompt)
            if stream:
                stream_run(run, self.console_tag, run_logger=self._run_logger)
            else:
                print_role(self.console_tag, "(运行中...)", run_logger=self._run_logger)
            result = run.wait()
        except CursorAgentError as error:
            print(
                f"启动失败: {error.message} (retryable={error.is_retryable})",
                file=sys.stderr,
            )
            raise
        if result.status == "error":
            raise RuntimeError(f"[{self.console_tag}] 运行失败 run_id={run.id}")
        response_text = run.text()
        if self._echo_plan:
            self._print_plan(run, response_text)
        return response_text

    def _print_plan(self, run, response_text: str) -> None:
        plan = extract_plan(run=run, agent=self._agent, response_text=response_text)
        if plan:
            print_role(
                f"{self.console_tag}/plan",
                plan,
                run_logger=self._run_logger,
            )
        else:
            print_role(
                f"{self.console_tag}/plan",
                "（本轮未检测到 plan）",
                run_logger=self._run_logger,
            )

    def close(self) -> None:
        self._agent.close()

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()
