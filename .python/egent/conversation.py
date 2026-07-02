"""Chat Completions 多轮对话封装。"""

from __future__ import annotations

from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI

ChatRole = Literal["system", "user", "assistant"]
ChatMessage = dict[str, str]


@dataclass(frozen=True)
class ConversationEvent:
    """Conversation 流式事件基类。"""


@dataclass(frozen=True)
class TextDelta(ConversationEvent):
    """LLM 输出的文本增量。"""

    text: str


@dataclass(frozen=True)
class TurnCompleted(ConversationEvent):
    """单轮对话结束，携带完整回复文本。"""

    text: str


class UnexpectedAssistantTurnError(ValueError):
    """上一条消息已是 assistant，无法继续 send。"""


class Conversation:
    """维护 messages 历史并调用 Chat Completions API。"""

    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        messages: list[ChatMessage] | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self._messages = _copy_messages(messages) if messages else []

    @property
    def messages(self) -> list[ChatMessage]:
        """返回当前聊天记录的副本。"""
        return _copy_messages(self._messages)

    def add_message(self, role: ChatRole, content: str) -> None:
        """追加一条消息，不发起请求。"""
        self._messages.append({"role": role, "content": content})

    async def send(
        self,
        *,
        add_to_history: bool = True,
    ) -> AsyncIterator[ConversationEvent]:
        """根据当前历史流式请求助手回复。"""
        if self._messages and self._messages[-1]["role"] == "assistant":
            raise UnexpectedAssistantTurnError(
                "上一条消息已是 assistant，请先追加 user 消息",
            )

        reply_parts: list[str] = []
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self._messages,
            stream=True,
        )
        async for chunk in stream:
            delta_text = chunk.choices[0].delta.content
            if delta_text:
                reply_parts.append(delta_text)
                yield TextDelta(delta_text)

        reply = "".join(reply_parts)
        if add_to_history:
            self.add_message("assistant", reply)
        yield TurnCompleted(reply)

    def clone(self) -> Conversation:
        """克隆一份聊天记录完全相同的独立会话。"""
        return Conversation(
            client=self.client,
            model=self.model,
            messages=self._messages,
        )


def _copy_messages(messages: list[ChatMessage]) -> list[ChatMessage]:
    return deepcopy(messages)
