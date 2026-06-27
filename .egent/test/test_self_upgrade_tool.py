"""测试自升级工作流工具注册与 schema。"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import workflow.agent_definition
import workflow.tools.self_upgrade_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "egent"


def test_self_upgrade_tool_schema() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            workflow.tools.self_upgrade_tool.run_self_upgrade,
        ),
    )
    assert binding.name == "self_upgrade_tool_run_self_upgrade"
    function = binding.schema["function"]
    assert "自升级" in function["description"]
    properties = function["parameters"]["properties"]
    assert properties["prompt"]["type"] == "string"
    assert "prompt" in function["parameters"]["required"]
    assert "agent_client" not in properties


def test_self_upgrade_tool_empty_prompt() -> None:
    wrapped = agent.tool_binding.wrap_tool(
        MockAgent(),
        workflow.tools.self_upgrade_tool.run_self_upgrade,
    )
    result = asyncio.run(wrapped(prompt="   "))
    assert "不能为空" in result


def test_egent_definition_includes_self_upgrade_tool() -> None:
    tool_names = {
        agent.tool_binding.resolve_tool_name(handler)
        for handler in workflow.agent_definition.AGENTS["egent"].default_tools
    }
    assert "self_upgrade_tool_run_self_upgrade" in tool_names


if __name__ == "__main__":
    test_self_upgrade_tool_schema()
    test_self_upgrade_tool_empty_prompt()
    test_egent_definition_includes_self_upgrade_tool()
    print("✅ self_upgrade_tool 测试通过")
