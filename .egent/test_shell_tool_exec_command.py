#!/usr/bin/env python
"""测试 shell_tool.exec_command 重命名后是否正常工作"""

import sys
import os

# 添加 .egent 到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.builtin_tools import shell_tool
from agent.agent_config import ADMIN_TOOLS

def test_exec_command_exists():
    """测试 exec_command 函数存在"""
    assert hasattr(shell_tool, 'exec_command'), "shell_tool 应该有 exec_command 函数"
    print("✓ exec_command 函数存在")

def test_exec_command_works():
    """测试 exec_command 能正常执行命令"""
    result = shell_tool.exec_command(None, 'echo test123')
    assert 'test123' in result, f"执行结果应该包含 'test123', 实际: {result}"
    print("✓ exec_command 执行命令正常")

def test_admin_tools_reference():
    """测试 ADMIN_TOOLS 正确引用了 exec_command"""
    # 找到 shell_tool.exec_command 在 ADMIN_TOOLS 中的位置
    tool_names = [tool.__name__ for tool in ADMIN_TOOLS]
    assert 'exec_command' in tool_names, f"ADMIN_TOOLS 应该包含 exec_command, 实际: {tool_names}"
    print(f"✓ ADMIN_TOOLS 正确引用 exec_command")
    print(f"  ADMIN_TOOLS: {tool_names}")

def test_no_builtin_exec_override():
    """测试没有覆盖内置 exec 函数"""
    # 内置 exec 应该仍然是 builtin 函数
    import builtins
    assert hasattr(builtins, 'exec'), "内置 exec 函数应该存在"
    # shell_tool 模块不应该有名为 exec 的属性（除非它导入了内置 exec）
    # 但我们重命名了函数，所以应该没有 exec 属性了
    has_exec = hasattr(shell_tool, 'exec')
    if has_exec:
        # 如果有 exec，它应该是内置函数，而不是我们的工具函数
        assert shell_tool.exec is builtins.exec, "shell_tool.exec 应该是内置 exec"
    print("✓ 没有覆盖内置 exec 函数")

if __name__ == '__main__':
    print("=== 测试 shell_tool.exec_command ===\n")
    
    test_exec_command_exists()
    test_exec_command_works()
    test_admin_tools_reference()
    test_no_builtin_exec_override()
    
    print("\n✅ 所有测试通过！")
