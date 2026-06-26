"""测试 tool_binding 从方法签名与 @param 文档生成 schema。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import agent.tools.grep_search_tool
import agent.tools.shell_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "test"


def test_grep_search_schema() -> None:
    tool = agent.tools.grep_search_tool.GrepSearchTool(MockAgent())
    binding = agent.tool_binding.build_binding(tool.grep_search)
    assert binding.name == "grep_search_tool_grep_search"
    function = binding.schema["function"]
    assert "正则" in function["description"]
    properties = function["parameters"]["properties"]
    assert properties["pattern"]["type"] == "string"
    assert "pattern" in function["parameters"]["required"]
    assert "directory" not in function["parameters"]["required"]
    assert "缺省" in properties["directory"]["description"]


def test_bg_tool_custom_name() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tools.shell_tool.BgTool(MockAgent()).bg_exec,
    )
    assert binding.name == "shell_tool_bg_exec"


def test_bind_all_builtin_names() -> None:
    from agent.agent_client import AgentClient
    from agent.agent_model import AgentModel

    import tool_handlers

    client = AgentClient(
        "test",
        AgentModel(api_key="", model="test", base_url="https://example.com/v1"),
        AgentConfig(),
    )
    client.tools = tool_handlers.build_default_tools(client)
    resolved = sorted(
        agent.tool_binding.resolve_tool_name(handler)
        for handler in client.tools
    )
    assert len(resolved) == len(agent.tool_binding.BUILTIN_TOOL_NAMES)
    assert resolved == sorted(agent.tool_binding.BUILTIN_TOOL_NAMES)


if __name__ == "__main__":
    test_grep_search_schema()
    test_bg_tool_custom_name()
    test_bind_all_builtin_names()
    print("✅ tool_binding 测试通过")
