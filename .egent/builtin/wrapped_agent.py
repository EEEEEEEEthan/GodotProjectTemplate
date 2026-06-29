"""封装 AgentClient，send 时自动打印流式输出与工具调用。"""

from __future__ import annotations

import sys

import openai

import agent.agent_client
import agent.agent_events
import agent.agent_tools
import agent.tool_binding

__DIM = "\033[90m"
__RESET = "\033[0m"


def write_line_colored(value: str, *, dim: bool = True) -> None:
    """向 stdout 输出一行，可选灰色。"""
    if dim:
        sys.stdout.write(f"{__DIM}{value}{__RESET}\n")
    else:
        sys.stdout.write(f"{value}\n")


def format_tool_header(
    event: agent.agent_events.ToolInvoking,
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
        self.__client = client
        self.__debug = debug

    @property
    def name(self) -> str:
        """代理名称。"""
        return self.__client.name

    @property
    def model(self) -> str:
        """模型标识。"""
        return self.__client.model

    @property
    def base_url(self) -> str:
        """API 地址。"""
        return self.__client.base_url

    @property
    def system_prompt(self) -> str:
        """系统提示词。"""
        return self.__client.system_prompt

    @property
    def tool_names(self) -> list[str]:
        """已注册工具名称列表。"""
        return self.__client.tool_names

    @property
    def tools(self) -> tuple[agent.tool_binding.ToolHandler, ...]:
        """已注册工具处理器元组。"""
        return self.__client.tools

    async def send(
        self,
        prompt: str,
        *,
        role: str = "user",
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None = None,
    ) -> list[str]:
        """发送消息并打印流式输出，返回每轮 TurnCompleted 的完整文本。"""
        completions: list[str] = []
        try:
            async for event in self.__client.send(
                role,
                prompt,
                override_tools=override_tools,
            ):
                self.__print_event(event)
                if isinstance(event, agent.agent_events.TurnCompleted):
                    completions.append(event.text)
        except agent.agent_client.STREAM_RETRYABLE_ERRORS as error:
            write_line_colored(
                f"API 连接中断（已重试仍失败）: {error}",
                dim=False,
            )
        except openai.APIError as error:
            write_line_colored(f"API 错误: {error}", dim=False)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return completions

    def __print_event(self, event: agent.agent_events.AgentEvent) -> None:
        if isinstance(event, agent.agent_events.TextDelta):
            sys.stdout.write(event.text)
            sys.stdout.flush()
        elif isinstance(event, agent.agent_events.ToolInvoking):
            try:
                if sys.stdout.isatty():
                    sys.stdout.write("\n")
            except OSError:
                pass
            write_line_colored(format_tool_header(event, debug=self.__debug))
        elif isinstance(event, agent.agent_events.ToolInvoked):
            if self.__debug and event.result:
                write_line_colored(event.result)

    async def aclose(self) -> None:
        """关闭客户端连接。"""
        await self.__client.aclose()
