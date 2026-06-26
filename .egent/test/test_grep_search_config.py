"""测试 grep_search_tool 是否正确使用配置文件中的 ignore_files"""

import os
import sys
import tempfile
import shutil

# 添加 .egent 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.agent_config import AgentConfig
import agent.builtin_tools.grep_search_tool as grep_search_tool_module

GrepSearchTool = grep_search_tool_module.GrepSearchTool


class MockAgent:
    """模拟 Agent 对象，用于测试"""
    def __init__(self, ignore_files):
        self.config = AgentConfig(ignore_files=ignore_files)


def test_grep_search_uses_config():
    """测试 GrepSearchTool 是否正确使用配置文件中的 ignore_files文件"""
    
    # 保存当前工作目录
    original_cwd = os.getcwd()
    
    # 创建临时目录结构
    with tempfile.TemporaryDirectory() as tmpdir:
        # 切换到工作目录
        os.chdir(tmpdir)
        
        try:
            # 创建一些测试文件
            test_dirs = [
                "normal_dir",
                ".git",
                ".godot",
                ".egent",
                "node_modules",
                "__pycache__",
            ]
            
            for dirname in test_dirs:
                dirpath = os.path.join(tmpdir, dirname)
                os.makedirs(dirpath)
                # 在每个目录中创建一个文件
                filepath = os.path.join(dirpath, "test.txt")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(f"content from {dirname}")
            
            # 测试1：使用默认配置（应该跳过 .git, .godot, .egent, node_modules, __pycache__）
            print("测试1：使用默认配置...")
            mock_agent = MockAgent(AgentConfig().ignore_files)
            grep_tool = GrepSearchTool(mock_agent)
            result = grep_tool.grep_search(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result}")
            
            # 检查是否只包含 normal_dir 和 .godot（.godot 不在默认配置中）
            assert "normal_dir/test.txt" in result, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" not in result, "不应该包含 .git/test.txt"
            # .godot 不在默认配置中，所以应该包含
            assert ".godot/test.txt" in result, "应该包含 .godot/test.txt（不在默认配置中）"
            assert ".egent/test.txt" not in result, "不应该包含 .egent/test.txt"
            assert "node_modules/test.txt" not in result, "不应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" not in result, "不应该包含 __pycache__/test.txt"
            
            print("✓ 测试1通过：默认配置正确跳过了指定目录")
            
            # 测试2：使用空配置（不应该跳过任何目录）
            print("\n测试2：使用空配置...")
            mock_agent2 = MockAgent([])
            grep_tool2 = GrepSearchTool(mock_agent2)
            result2 = grep_tool2.grep_search(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result2}")
            
            # 检查是否包含所有目录
            assert "normal_dir/test.txt" in result2, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" in result2, "应该包含 .git/test.txt"
            assert ".godot/test.txt" in result2, "应该包含 .godot/test.txt"
            assert ".egent/test.txt" in result2, "应该包含 .egent/test.txt"
            assert "node_modules/test.txt" in result2, "应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" in result2, "应该包含 __pycache__/test.txt"
            
            print("✓ 测试2通过：空配置不跳过任何目录")
            
            # 测试3：使用自定义配置（只跳过 .git）
            print("\n测试3：使用自定义配置（只跳过 .git）...")
            mock_agent3 = MockAgent([".git"])
            grep_tool3 = GrepSearchTool(mock_agent3)
            result3 = grep_tool3.grep_search(pattern="content from", directory=".", **{"filter": "*.txt"})
            
            print(f"结果：\n{result3}")
            
            # 检查是否只跳过 .git
            assert "normal_dir/test.txt" in result3, "应该包含 normal_dir/test.txt"
            assert ".git/test.txt" not in result3, "不应该包含 .git/test.txt"
            assert ".godot/test.txt" in result3, "应该包含 .godot/test.txt"
            assert ".egent/test.txt" in result3, "应该包含 .egent/test.txt"
            assert "node_modules/test.txt" in result3, "应该包含 node_modules/test.txt"
            assert "__pycache__/test.txt" in result3, "应该包含 __pycache__/test.txt"
            
            print("✓ 测试3通过：自定义配置正确工作")
        finally:
            # 恢复工作目录
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_grep_search_uses_config()
    print("\n✅ 所有测试通过！")
