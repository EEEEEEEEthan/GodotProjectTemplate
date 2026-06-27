"""业务层工具集构建：按场景组装 Agent 可调用的工具方法列表。"""

from __future__ import annotations

import typing

import agent.agent_config
import agent.tool_binding

if typing.TYPE_CHECKING:
    import agent.agent_client


def get_all_tools(
    agent_client: agent.agent_client.AgentClient,
) -> list[agent.tool_binding.ToolHandler]:
    """返回全量工具集。"""
    return agent.agent_config.get_default_tools(agent_client)
