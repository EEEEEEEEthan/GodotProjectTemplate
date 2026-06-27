"""测试 tool_binding 从方法签名与 @param 文档生成 schema。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import agent.builtin_tools.grep_search_tool
import agent.builtin_tools.shell_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "test"


def test_grep_search_schema() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            agent.builtin_tools.grep_search_tool.grep_search,
        ),
    )
    assert binding.name == "grep_search_tool_grep_search"
    function = binding.schema["function"]
    assert "正则" in function["description"]
    properties = function["parameters"]["properties"]
    assert properties["pattern"]["type"] == "string"
    assert "pattern" in function["parameters"]["required"]
    assert "directory" not in function["parameters"]["required"]
    assert "agent_client" not in properties
    assert "缺省" in properties["directory"]["description"]


def test_bg_tool_custom_name() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            agent.builtin_tools.shell_tool.bg_exec,
        ),
    )
    assert binding.name == "shell_tool_bg_exec"


def test_bind_all_builtin_tools() -> None:
    from agent.agent_client import AgentClient
    from agent.agent_model import AgentModel

    config = AgentConfig()
    client = AgentClient(
        "test",
        AgentModel(api_key="", model="test", base_url="https://example.com/v1"),
        config,
    )
    client.tools = config.default_tools(client)
    resolved = [
        agent.tool_binding.resolve_tool_name(handler)
        for handler in client.tools
    ]
    bindings = agent.tool_binding.bind_tools(*client.tools)
    assert len(resolved) == len(client.tools)
    assert len(resolved) == len(bindings)
    assert len(resolved) == len(set(resolved))
    assert sorted(bindings.keys()) == sorted(resolved)


if __name__ == "__main__":
    test_grep_search_schema()
    test_bg_tool_custom_name()
    test_bind_all_builtin_tools()
    print("✅ tool_binding 测试通过")
