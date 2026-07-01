"""测试 egent 自动化测试工具。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import agent_definition
import tools.egent_test_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "egent"


def test_egent_test_tool_schema() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            tools.egent_test_tool.run_egent_test,
        ),
    )
    assert binding.name == "egent_test_tool_run_egent_test"
    function = binding.schema["function"]
    assert "test_*.py" in function["description"]
    assert function["parameters"]["properties"] == {}
    assert "agent_client" not in function["parameters"]["properties"]


def test_egent_test_tool_runs() -> None:
    if os.environ.get("EGENT_TEST_NESTED"):
        return  # 避免递归：嵌套子进程无需再跑 run_egent_test
    wrapped = agent.tool_binding.wrap_tool(
        MockAgent(),
        tools.egent_test_tool.run_egent_test,
    )
    result = wrapped()
    assert "egent 测试" in result
    assert "总计:" in result


def test_egent_definition_includes_egent_test_tool() -> None:
    tool_names = {
        agent.tool_binding.resolve_tool_name(handler)
        for handler in agent_definition.AGENTS["egent"].default_tools
    }
    assert "egent_test_tool_run_egent_test" in tool_names


def test_jack_definition_includes_egent_test_tool() -> None:
    tool_names = {
        agent.tool_binding.resolve_tool_name(handler)
        for handler in agent_definition.AGENTS["jack"].default_tools
    }
    assert "egent_test_tool_run_egent_test" in tool_names


if __name__ == "__main__":
    test_egent_test_tool_schema()
    test_egent_test_tool_runs()
    test_egent_definition_includes_egent_test_tool()
    test_jack_definition_includes_egent_test_tool()
    print("✅ egent_test_tool 测试通过")
