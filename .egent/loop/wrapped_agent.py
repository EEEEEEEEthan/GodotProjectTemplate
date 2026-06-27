"""封装 AgentClient，send 时自动打印流式输出与工具调用。"""

from __future__ import annotations

import sys

import openai

import agent.agent_client
import agent.agent_events
import agent.agent_tools
import loop.agent_config

__DIM = "\033[90m"
__RESET = "\033[0m"


def write_line_colored(value: str, *, dim: bool = True) -> None:
    """向 stdout 输出一行，可选灰色。"""
    if dim:
        sys.stdout.write(f"{__DIM}{value}{__RESET}\n")
    else:
        sys.stdout.write(f"{value}\n")


def format_tool_header(
    event: agent.agent_events.ToolInvoked,
    *,
    debug: bool,
) -> str:
    """按调试模式格式化工具调用摘要行。"""
    if debug:
        arguments_text = agent.agent_tools.format_tool_arguments(event.arguments)
    else:
        arguments_text = agent.agent_tools.format_tool_arguments_brief(event.arguments)
    if not arguments_text:
        return f"[{event.name}]"
    return f"[{event.name}] {arguments_text}"


class WrappedAgent:
    """封装 AgentClient，send 时自动打印文本与工具调用。"""

    def __init__(
        self,
        client: agent.agent_client.AgentClient,
        *,
        debug: bool = False,
    ) -> None:
        self._client = client
        self._debug = debug

    @classmethod
    def from_name(cls, name: str, *, debug: bool = False) -> WrappedAgent:
        """按 agent 名称构造。"""
        return loop.agent_config.get_definition(name).instantiate(debug=debug)

    @property
    def client(self) -> agent.agent_client.AgentClient:
        return self._client

    @property
    def name(self) -> str:
        return self._client.name

    async def prepare(self) -> None:
        await self._client.prepare()

    async def send(self, prompt: str, *, role: str = "user") -> None:
        """发送消息并打印流式输出。"""
        try:
            async for event in self._client.send(role, prompt):
                self.__print_event(event)
        except agent.agent_client.STREAM_RETRYABLE_ERRORS as error:
            write_line_colored(
                f"API 连接中断（已重试仍失败）: {error}",
                dim=False,
            )
        except openai.APIError as error:
            write_line_colored(f"API 错误: {error}", dim=False)
        sys.stdout.write("\n")
        sys.stdout.flush()

    def __print_event(self, event: agent.agent_events.AgentEvent) -> None:
        if isinstance(event, agent.agent_events.TextDelta):
            sys.stdout.write(event.text)
            sys.stdout.flush()
        elif isinstance(event, agent.agent_events.ToolInvoked):
            try:
                if sys.stdout.isatty():
                    sys.stdout.write("\n")
            except OSError:
                pass
            write_line_colored(format_tool_header(event, debug=self._debug))
            if self._debug and event.result:
                write_line_colored(event.result)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> WrappedAgent:
        await self.prepare()
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()


def get_agent(name: str, *, debug: bool = False) -> WrappedAgent:
    """按名称创建 WrappedAgent。"""
    return WrappedAgent.from_name(name, debug=debug)
