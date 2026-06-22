"""Cursor SDK agent 会话封装。"""

import sys
from pathlib import Path

from cursor_sdk import Agent, AgentOptions, Client, CursorAgentError, LocalAgentOptions

from config import DEFAULT_MODEL, PROJECT_ROOT


def load_prompt(name: str) -> str:
    path = Path(__file__).resolve().parent / "prompts" / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def print_role(role_label: str, text: str) -> None:
    print(f"\n[{role_label}]\n{text}\n")


def stream_run(run, role_label: str) -> None:
    print(f"\n[{role_label}] ", end="", flush=True)
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
        role_label: str,
        system_prompt: str,
        *,
        client: Client,
        mode: str,
        model: str = DEFAULT_MODEL,
        api_key: str | None = None,
        cwd: Path = PROJECT_ROOT,
    ) -> None:
        self.role_label = role_label
        self.system_prompt = system_prompt
        self._bootstrapped = False
        options = AgentOptions(
            api_key=api_key,
            model=model,
            mode=mode,
            local=LocalAgentOptions(cwd=str(cwd), setting_sources=[]),
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
                stream_run(run, self.role_label)
            else:
                print_role(self.role_label, "(运行中...)")
            result = run.wait()
        except CursorAgentError as error:
            print(
                f"启动失败: {error.message} (retryable={error.is_retryable})",
                file=sys.stderr,
            )
            raise
        if result.status == "error":
            raise RuntimeError(f"[{self.role_label}] 运行失败 run_id={run.id}")
        return run.text()

    def close(self) -> None:
        self._agent.close()

    def __enter__(self) -> "AgentSession":
        return self

    def __exit__(self, *args) -> None:
        self.close()
