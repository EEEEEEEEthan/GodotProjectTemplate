"""测试 grep_search_tool 是否正确使用配置文件中的 ignore_files"""

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


def test_grep_search_uses_config():
    """测试 grep_search 是否正确使用配置文件中的 ignore_files"""
    
    original_cwd = os.getcwd()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        
        try:
            test_dirs = [
                "normal_dir",
                ".git",
                ".godot",
                os.path.join("addons", "egent"),
                "node_modules",
                "__pycache__",
            ]
            
            for dirname in test_dirs:
                dirpath = os.path.join(tmpdir, dirname)
                os.makedirs(dirpath)
                filepath = os.path.join(dirpath, "test.txt")
                with open(filepath, 'w', encoding='utf-8') as handle:
                    handle.write(f"content from {dirname}")
            
            print("测试1：使用默认配置...")
            mock_agent = MockAgent(AgentConfig().ignore_files)
            grep_handler = agent.tool_binding.wrap_tool(
                mock_agent,
                grep_search_tool_module.grep_search,
            )
            result = grep_handler(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result}")
            
            assert "normal_dir/test.txt" in result, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" not in result, "不应该包含 .git/test.txt"
            assert ".godot/test.txt" in result, "应该包含 .godot/test.txt（不在默认配置中）"
            assert "addons/egent/test.txt" not in result, "不应该包含 addons/egent/test.txt"
            assert "node_modules/test.txt" not in result, "不应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" not in result, "不应该包含 __pycache__/test.txt"
            
            print("✓ 测试1通过：默认配置正确跳过了指定目录")
            
            print("\n测试2：使用空配置...")
            mock_agent2 = MockAgent([])
            grep_handler2 = agent.tool_binding.wrap_tool(
                mock_agent2,
                grep_search_tool_module.grep_search,
            )
            result2 = grep_handler2(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result2}")
            
            assert "normal_dir/test.txt" in result2, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" in result2, "应该包含 .git/test.txt"
            assert ".godot/test.txt" in result2, "应该包含 .godot/test.txt"
            assert "addons/egent/test.txt" in result2, "应该包含 addons/egent/test.txt"
            assert "node_modules/test.txt" in result2, "应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" in result2, "应该包含 __pycache__/test.txt"
            
            print("✓ 测试2通过：空配置不跳过任何目录")
            
            print("\n测试3：使用自定义配置（只跳过 .git）...")
            mock_agent3 = MockAgent([".git"])
            grep_handler3 = agent.tool_binding.wrap_tool(
                mock_agent3,
                grep_search_tool_module.grep_search,
            )
            result3 = grep_handler3(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result3}")
            
            assert "normal_dir/test.txt" in result3, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" not in result3, "不应该包含 .git/test.txt"
            assert ".godot/test.txt" in result3, "应该包含 .godot/test.txt"
            assert "addons/egent/test.txt" in result3, "应该包含 addons/egent/test.txt"
            assert "node_modules/test.txt" in result3, "应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" in result3, "应该包含 __pycache__/test.txt"
            
            print("✓ 测试3通过：自定义配置正确工作")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_grep_search_uses_config()
    print("\n✅ 所有测试通过！")
