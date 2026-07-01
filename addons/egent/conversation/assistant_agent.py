"""默认单 agent 工厂。"""

from __future__ import annotations

from agents import Agent, Tool

from .model_runtime import ModelRuntime

DEFAULT_ASSISTANT_INSTRUCTIONS = """你是一个有用的 AI 助手。
回答要准确、简洁；不确定时明确说明。"""


def create_assistant_agent(
    model_runtime: ModelRuntime,
    *,
    name: str = "助手",
    instructions: str | None = None,
    tools: list[Tool] | None = None,
) -> Agent:
    resolved_instructions = (
        instructions
        or model_runtime.config.instructions
        or DEFAULT_ASSISTANT_INSTRUCTIONS
    )
    return Agent(
        name=name,
        instructions=resolved_instructions,
        model=model_runtime.model_name,
        tools=tools or [],
    )
