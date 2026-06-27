"""Agent 流式事件类型：文本增量、工具调用与回合结束。"""

from __future__ import annotations

import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class AgentEvent:
    """Agent 流式事件基类。"""


@dataclasses.dataclass(frozen=True)
class TextDelta(AgentEvent):
    """LLM 输出的文本增量。"""

    text: str


@dataclasses.dataclass(frozen=True)
class ToolInvoking(AgentEvent):
    """工具调用即将开始（尚未执行）。"""

    name: str
    arguments: dict[str, typing.Any]


@dataclasses.dataclass(frozen=True)
class ToolInvoked(AgentEvent):
    """一次工具调用及其返回结果。"""

    name: str
    arguments: dict[str, typing.Any]
    result: str


@dataclasses.dataclass(frozen=True)
class TurnCompleted(AgentEvent):
    """单轮对话结束，携带完整回复文本。"""

    text: str
