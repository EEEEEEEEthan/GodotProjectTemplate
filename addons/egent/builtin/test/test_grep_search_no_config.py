"""测试配置文件缺失时的行为"""

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


def test_no_config():
    """测试配置文件缺失时，不跳过任何目录"""
    original_cwd = os.getcwd()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        try:
            os.makedirs(".git")
            os.makedirs("normal_dir")
            
            with open(".git/test.txt", 'w', encoding='utf-8') as handle:
                handle.write("git content")
            with open("normal_dir/test.txt", 'w', encoding='utf-8') as handle:
                handle.write("normal content")
            
            mock_agent = MockAgent([])
            grep_handler = agent.tool_binding.wrap_tool(
                mock_agent,
                grep_search_tool_module.grep_search,
            )
            
            result = grep_handler(pattern="content", directory=".", **{"filter": "*.txt"})
            print(f"结果:\n{result}")
            
            assert ".git/test.txt" in result, "应该包含 .git/test.txt（配置为空时不跳过）"
            assert "normal_dir/test.txt" in result, "应该包含 normal_dir/test.txt"
            
            print("✓ 测试通过：配置为空时不跳过任何目录")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_no_config()
    print("\n✅ 测试通过！")
