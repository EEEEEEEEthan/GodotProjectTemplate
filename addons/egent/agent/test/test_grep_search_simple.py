"""简单测试 grep_search 工具"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.agent_config import AgentConfig
import tools.grep_search_tool as grep_search_tool_module
import agent.tool_binding


class MockAgent:
    """模拟 Agent 对象，用于测试"""
    def __init__(self, ignore_files):
        self.config = AgentConfig(ignore_files=ignore_files)


def test_simple():
    """简单测试"""
    original_cwd = os.getcwd()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        try:
            os.makedirs("test_dir")
            with open("test_dir/test.txt", 'w', encoding='utf-8') as handle:
                handle.write("hello world")
            
            mock_agent = MockAgent([])
            grep_handler = agent.tool_binding.wrap_tool(
                mock_agent,
                grep_search_tool_module.grep_search,
            )
            
            result = grep_handler(pattern="hello", directory=".", **{"filter": "*.txt"})
            print(f"结果: {result}")
            
            assert "test_dir/test.txt" in result
            print("✓ 测试通过")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_simple()
