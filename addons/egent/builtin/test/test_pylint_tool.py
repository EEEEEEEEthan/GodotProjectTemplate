"""测试 pylint 工作流工具。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import agent_definition
import tools.pylint_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "egent"


def test_pylint_tool_schema() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            tools.pylint_tool.run_pylint,
        ),
    )
    assert binding.name == "pylint_tool_run_pylint"
    function = binding.schema["function"]
    assert "pylint" in function["description"].lower()
    properties = function["parameters"]["properties"]
    assert properties["paths"]["type"] == "string"
    assert properties["timeout"]["type"] == "integer"
    assert "agent_client" not in properties


def test_pylint_tool_invalid_path() -> None:
    wrapped = agent.tool_binding.wrap_tool(
        MockAgent(),
        tools.pylint_tool.run_pylint,
    )
    result = wrapped(paths="../outside")
    assert "必须在 addons/egent 内" in result


def test_pylint_tool_runs() -> None:
    wrapped = agent.tool_binding.wrap_tool(
        MockAgent(),
        tools.pylint_tool.run_pylint,
    )
    result = wrapped(paths="builtin/tools")
    assert "检查范围" in result


def test_egent_definition_includes_pylint_tool() -> None:
    tool_names = {
        agent.tool_binding.resolve_tool_name(handler)
        for handler in agent_definition.AGENTS["egent"].default_tools
    }
    assert "pylint_tool_run_pylint" in tool_names


def test_nahte_definition_includes_pylint_tool() -> None:
    tool_names = {
        agent.tool_binding.resolve_tool_name(handler)
        for handler in agent_definition.AGENTS["nahte"].default_tools
    }
    assert "pylint_tool_run_pylint" in tool_names


if __name__ == "__main__":
    test_pylint_tool_schema()
    test_pylint_tool_invalid_path()
    test_pylint_tool_runs()
    test_egent_definition_includes_pylint_tool()
    test_nahte_definition_includes_pylint_tool()
    print("✅ pylint_tool 测试通过")
