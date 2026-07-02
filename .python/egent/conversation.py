"""Chat Completions 多轮对话封装。"""

from __future__ import annotations

import pathlib
import uuid
from collections.abc import AsyncIterator, Awaitable, Iterable
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Literal

from openai import AsyncOpenAI, NOT_GIVEN

from egent.limits import TOOL_RESULT_MAX_CHARS
from egent.model_settings import ModelSettings, ensure_egent_gitignore
from egent.tool import ToolCallable, resolve_tools

ChatRole = Literal["system", "user", "assistant", "tool"]
ChatMessage = dict[str, Any]

_EGENT_TEMP_DIR = pathlib.Path.cwd() / ".egent" / ".temp"


@dataclass(frozen=True)
class ConversationEvent:
    """Conversation 流式事件基类。"""


@dataclass(frozen=True)
class TextDelta(ConversationEvent):
    """LLM 输出的文本增量。"""

    text: str


@dataclass(frozen=True)
class ToolCallStarted(ConversationEvent):
    """工具调用即将执行。"""

    name: str
    arguments: str


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
        settings: str,
        messages: list[ChatMessage] | None = None,
    ) -> None:
        """初始化对话会话。

        Args:
            settings: ``.egent/.model.toml`` 中的 profile 名（相对运行目录 ``cwd``）。
            messages: 初始聊天记录；省略时从空历史开始。
        """
        self._settings = ModelSettings.load(settings)
        self._client = AsyncOpenAI(
            api_key=self._settings.api_key,
            base_url=self._settings.base_url,
        )
        self.model = self._settings.model_name
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
        tools: Iterable[ToolCallable] = (),
    ) -> AsyncIterator[ConversationEvent]:
        """根据当前历史流式请求助手回复，必要时自动执行工具并续聊。"""
        api_tools, tool_handlers = resolve_tools(list(tools))

        while True:
            async with self._client.chat.completions.stream(
                model=self.model,
                messages=self._messages,
                tools=api_tools if api_tools else NOT_GIVEN,
            ) as stream:
                async for event in stream:
                    if event.type == "content.delta":
                        yield TextDelta(event.delta)

                completion = await stream.get_final_completion()

            message = completion.choices[0].message
            reply_text = message.content or ""
            tool_calls = message.tool_calls or []
            if not tool_calls:
                self.add_message("assistant", reply_text)
                yield TurnCompleted(reply_text)
                return

            self._messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in tool_calls
                ],
            })

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_arguments = tool_call.function.arguments
                handler = tool_handlers.get(function_name)
                if handler is None:
                    raise ValueError(f"未注册工具处理器: {function_name}")

                yield ToolCallStarted(
                    name=function_name,
                    arguments=function_arguments,
                )
                handler_result = handler(function_arguments)
                if isinstance(handler_result, Awaitable):
                    handler_result = await handler_result
                handler_result = _limit_tool_result(handler_result, function_name)

                yield ToolCallExecuted(
                    name=function_name,
                    arguments=function_arguments,
                    result=handler_result,
                )
                self._messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": handler_result,
                })


def _limit_tool_result(content: str, tool_name: str) -> str:
    if len(content) <= TOOL_RESULT_MAX_CHARS:
        return content

    head = content[:TOOL_RESULT_MAX_CHARS]
    tail = content[TOOL_RESULT_MAX_CHARS:]
    _EGENT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ensure_egent_gitignore()
    file_name = f"{tool_name}-{uuid.uuid4().hex}.txt"
    (_EGENT_TEMP_DIR / file_name).write_text(content, encoding="utf-8")
    relative_path = f".egent/.temp/{file_name}"
    return (
        f"{head}...\n"
        f"(内容太长被截断,剩余{len(tail)}字符,完整内容保存于{relative_path})"
    )


def _copy_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return deepcopy(messages)
