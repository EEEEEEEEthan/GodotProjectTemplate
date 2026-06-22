"""Cursor SDK agent 会话封装。"""

import sys
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, Client, CursorAgentError, LocalAgentOptions

from config import DEFAULT_MODEL, PROJECT_ROOT, SETTINGS_DIR, load_role_setting_sources
from plan_extract import extract_plan


def load_role_prompt(role_key: str) -> str:
    path = SETTINGS_DIR / f"{role_key}.txt"
    return path.read_text(encoding="utf-8")


def print_role(tag: str, text: str) -> None:
    print(f"\n[{tag}]\n{text}\n")


def stream_run(run, tag: str) -> None:
    print(f"\n[{tag}] ", end="", flush=True)
    for message in run.messages():
        if message.type != "assistant":
            continue
        for block in message.message.content:
            if block.type == "text" and block.text:
                print(block.text, end="", flush=True)
    print(flush=True)


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
    ) -> None:
        self.role_key = role_key
        self.console_tag = console_tag or role_key
        self.system_prompt = system_prompt
        self._bootstrapped = False
        self._echo_plan = echo_plan
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
        try:
            run = self._agent.send(prompt)
            if stream:
                stream_run(run, self.console_tag)
            else:
                print_role(self.console_tag, "(运行中...)")
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
            print_role(f"{self.console_tag}/plan", plan)
        else:
            print_role(f"{self.console_tag}/plan", "（本轮未检测到 plan）")

    def close(self) -> None:
        self._agent.close()

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()
