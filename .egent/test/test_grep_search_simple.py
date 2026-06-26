"""简单测试 GrepSearchTool"""

import os
import sys
import tempfile

# 添加 .egent 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.agent_config import AgentConfig
import agent.builtin_tools.grep_search_tool as grep_search_tool_module

GrepSearchTool = grep_search_tool_module.GrepSearchTool


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
            # 创建测试文件
            os.makedirs("test_dir")
            with open("test_dir/test.txt", 'w', encoding='utf-8') as f:
                f.write("hello world")
            
            # 创建工具实例
            mock_agent = MockAgent([])
            grep_tool = GrepSearchTool(mock_agent)
            
            # 调用方法（使用关键字参数）
            result = grep_tool.grep_search(pattern="hello", directory=".", **{"filter": "*.txt"})
            print(f"结果: {result}")
            
            assert "test_dir/test.txt" in result
            print("✓ 测试通过")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_simple()
