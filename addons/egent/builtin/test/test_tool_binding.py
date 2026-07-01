"""测试 tool_binding 从方法签名与 @param 文档生成 schema。"""

from __future__ import annotations

import json
import os
import pathlib
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.tool_binding
import tools.grep_search_tool
import tools.shell_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self) -> None:
        self.config = AgentConfig()
        self.name = "test"


def test_grep_search_schema() -> None:
    binding = agent.tool_binding.build_binding(
        agent.tool_binding.wrap_tool(
            MockAgent(),
            tools.grep_search_tool.grep_search,
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
            tools.shell_tool.bg_exec,
        ),
    )
    assert binding.name == "shell_tool_bg_exec"


def test_override_tools_wraps_agent_client() -> None:
    """override_tools 传入原始 handler 时也应注入 agent_client。"""
    import tempfile
    import tools.fuck_tool
    from agent.agent_client import AgentClient
    from agent.agent_model import AgentModel

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        original_data_dir = tools.fuck_tool._DATA_DIR
        tools.fuck_tool._DATA_DIR = temp_path
        tools.fuck_tool._FUCK_PATH = temp_path / "fuck.json"
        try:
            client = AgentClient(
                "jack",
                AgentModel(api_key="", model="test", base_url="https://example.com/v1"),
                AgentConfig(),
            )
            wrapped_handlers = client._AgentClient__resolve_send_handlers(
                (tools.fuck_tool.fuck,),
            )
            assert len(wrapped_handlers) == 1
            binding = agent.tool_binding.build_binding(wrapped_handlers[0])
            assert "agent_client" not in binding.schema["function"]["parameters"]["properties"]
            result = wrapped_handlers[0](complaint="override 注入测试")
            assert "收到" in result
            stored = json.loads((temp_path / "fuck.json").read_text(encoding="utf-8"))
            assert stored["items"][-1]["author"] == "jack"
        finally:
            tools.fuck_tool._DATA_DIR = original_data_dir
            tools.fuck_tool._FUCK_PATH = original_data_dir / "fuck.json"


def test_bind_all_builtin_tools() -> None:
    from agent.agent_client import AgentClient
    from agent.agent_model import AgentModel

    config = AgentConfig()
    client = AgentClient(
        "test",
        AgentModel(api_key="", model="test", base_url="https://example.com/v1"),
        config,
    )
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
    test_override_tools_wraps_agent_client()
    test_bind_all_builtin_tools()
    print("✅ tool_binding 测试通过")
