"""Chat Completions 多轮对话封装。"""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal, TYPE_CHECKING

from openai import AsyncOpenAI, NOT_GIVEN
from openai.types.chat.chat_completion_tool_union_param import (
    ChatCompletionToolUnionParam,
)

from egent.tool import ToolCallable, ToolHandler, resolve_tools

if TYPE_CHECKING:
    from egent.model_settings import ModelSettings

ChatRole = Literal["system", "user", "assistant", "tool"]
ChatMessage = dict[str, Any]


@dataclass(frozen=True)
class ConversationEvent:
    """Conversation 流式事件基类。"""


@dataclass(frozen=True)
class TextDelta(ConversationEvent):
    """LLM 输出的文本增量。"""

    text: str


@dataclass(frozen=True)
class ToolCallExecuted(ConversationEvent):
    """工具调用已执行并写回结果。"""

    name: str
    arguments: str
    result: str


@dataclass(frozen=True)
class TurnCompleted(ConversationEvent):
    """单轮对话结束，携带完整回复文本。"""

    text: str


class Conversation:
    """维护 messages 历史并调用 Chat Completions API。"""

    def __init__(
        self,
        settings: ModelSettings,
        messages: list[ChatMessage] | None = None,
    ) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )
        self.model = settings.model_name
        self._messages = _copy_messages(messages) if messages else []

    @property
    def messages(self) -> list[ChatMessage]:
        """返回当前聊天记录的副本。"""
        return _copy_messages(self._messages)

    def add_message(self, role: ChatRole, content: str) -> None:
        """追加一条消息，不发起请求。"""
        self._messages.append({"role": role, "content": content})

    async def request(
        self,
        *,
        tools: Iterable[ToolCallable] | None = None,
    ) -> AsyncIterator[ConversationEvent]:
        """根据当前历史流式请求助手回复，必要时自动执行工具并续聊。"""
        api_tools: list[ChatCompletionToolUnionParam] | None = None
        tool_handlers: dict[str, ToolHandler] | None = None
        if tools is not None:
            api_tools, tool_handlers = resolve_tools(list(tools))

        while True:
            reply_parts: list[str] = []
            tool_calls_by_index: dict[int, dict[str, Any]] = {}
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=self._messages,
                stream=True,
                tools=api_tools if api_tools is not None else NOT_GIVEN,
            )
            async for chunk in stream:
                choice_delta = chunk.choices[0].delta
                delta_text = choice_delta.content
                if delta_text:
                    reply_parts.append(delta_text)
                    yield TextDelta(delta_text)
                if choice_delta.tool_calls:
                    _merge_tool_call_deltas(
                        tool_calls_by_index,
                        choice_delta.tool_calls,
                    )

            reply_text = "".join(reply_parts)
            tool_calls = [
                tool_calls_by_index[index]
                for index in sorted(tool_calls_by_index)
            ]
            if not tool_calls:
                self.add_message("assistant", reply_text)
                yield TurnCompleted(reply_text)
                return

            if tool_handlers is None:
                raise ValueError("模型返回了工具调用，但未提供 tools。")

            assistant_message: ChatMessage = {
                "role": "assistant",
                "content": reply_text or None,
                "tool_calls": tool_calls,
            }
            self._messages.append(assistant_message)

            for tool_call in tool_calls:
                function_name = tool_call["function"]["name"]
                function_arguments = tool_call["function"]["arguments"]
                handler = tool_handlers.get(function_name)
                if handler is None:
                    raise ValueError(f"未注册工具处理器: {function_name}")

                handler_result = handler(function_arguments)
                if isinstance(handler_result, Awaitable):
                    handler_result = await handler_result

                yield ToolCallExecuted(
                    name=function_name,
                    arguments=function_arguments,
                    result=handler_result,
                )
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": handler_result,
                })

    def clone(self) -> Conversation:
        """克隆一份聊天记录完全相同的独立会话。"""
        return Conversation(
            settings=self._settings,
            messages=self._messages,
        )


def _merge_tool_call_deltas(
    tool_calls_by_index: dict[int, dict[str, Any]],
    tool_call_deltas: Iterable[Any],
) -> None:
    for tool_call_delta in tool_call_deltas:
        index = tool_call_delta.index
        if index not in tool_calls_by_index:
            tool_calls_by_index[index] = {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""},
            }

        accumulated_tool_call = tool_calls_by_index[index]
        if tool_call_delta.id:
            accumulated_tool_call["id"] = tool_call_delta.id
        if tool_call_delta.function is None:
            continue
        if tool_call_delta.function.name:
            accumulated_tool_call["function"]["name"] += (
                tool_call_delta.function.name
            )
        if tool_call_delta.function.arguments:
            accumulated_tool_call["function"]["arguments"] += (
                tool_call_delta.function.arguments
            )


def _copy_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return deepcopy(messages)
