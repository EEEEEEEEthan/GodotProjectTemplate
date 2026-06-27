"""业务层工具集构建：按场景组装 Agent 可调用的工具方法列表。"""

from __future__ import annotations

import typing

import agent.tool_binding

if typing.TYPE_CHECKING:
    import agent.agent_client


def get_all_tools(
    agent_client: agent.agent_client.AgentClient,
) -> tuple[agent.tool_binding.ToolHandler, ...]:
    """返回全量工具集（已注入 client）。"""
    return agent.tool_binding.wrap_tools(agent_client, *agent_client.config.default_tools)
