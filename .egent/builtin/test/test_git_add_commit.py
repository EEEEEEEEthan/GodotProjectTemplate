"""测试 git_add 和 git_commit 工具"""

import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agent.agent_config import AgentConfig
import tools.git_tool as git_tool_module
import agent.tool_binding


class MockAgent:
    """模拟 Agent 对象，用于测试"""

    def __init__(self):
        self.config = AgentConfig()


def _run_git(*args: str, cwd: str) -> None:
    """在指定目录执行 git 命令。"""
    subprocess.run(["git"] + list(args), cwd=cwd, check=True,
                   capture_output=True, text=True)


def test_git_add_and_commit():
    """测试 git add 和 git commit 的正常流程与边界情况。"""
    original_cwd = os.getcwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        try:
            _run_git("init", cwd=tmpdir)
            _run_git("config", "user.email", "test@test.com", cwd=tmpdir)
            _run_git("config", "user.name", "Test", cwd=tmpdir)

            mock_agent = MockAgent()
            add_handler = agent.tool_binding.wrap_tool(mock_agent, git_tool_module.git_add)
            commit_handler = agent.tool_binding.wrap_tool(mock_agent, git_tool_module.git_commit)

            # 创建文件
            with open("new_file.txt", "w", encoding="utf-8") as f:
                f.write("content\n")

            # git add
            result_add = add_handler(paths="new_file.txt")
            print(f"add 结果: {result_add}")

            # git commit
            result_commit = commit_handler(message="test: add new_file.txt")
            print(f"commit 结果: {result_commit}")

            # 验证提交成功
            log_result = subprocess.run(
                ["git", "log", "--oneline"],
                capture_output=True, text=True, cwd=tmpdir, check=False,
            )
            assert "add new_file.txt" in log_result.stdout, f"提交未生成: {log_result.stdout}"

            # 测试空 message
            result_empty = commit_handler(message="")
            print(f"空 message 结果: {result_empty}")
            assert "错误" in result_empty

            # 测试绝对路径
            result_bad = add_handler(paths=os.path.abspath("/"))
            print(f"绝对路径结果: {result_bad}")
            assert "错误" in result_bad

            # 测试 add 全部（缺省 .）
            with open("another.txt", "w", encoding="utf-8") as f:
                f.write("more\n")
            result_all = add_handler()
            print(f"add all 结果: {result_all}")

            print("✓ 测试通过")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_git_add_and_commit()
