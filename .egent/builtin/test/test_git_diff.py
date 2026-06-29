"""测试 git_diff 工具"""

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

    def __init__(self, ignore_files):
        self.config = AgentConfig(ignore_files=ignore_files)


def _run_git(*args: str, cwd: str) -> None:
    """在指定目录执行 git 命令。"""
    subprocess.run(["git"] + list(args), cwd=cwd, check=True,
                   capture_output=True, text=True)


def test_basic_diff():
    """基本功能测试：在临时 git 仓库中验证 git diff 输出"""
    original_cwd = os.getcwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        try:
            # 初始化 git 仓库
            _run_git("init", cwd=tmpdir)
            _run_git("config", "user.email", "test@test.com", cwd=tmpdir)
            _run_git("config", "user.name", "Test", cwd=tmpdir)

            # 创建初始文件并提交
            with open("hello.txt", "w", encoding="utf-8") as handle:
                handle.write("hello world\n")
            _run_git("add", "hello.txt", cwd=tmpdir)
            _run_git("commit", "-m", "initial", cwd=tmpdir)

            # 修改文件
            with open("hello.txt", "a", encoding="utf-8") as handle:
                handle.write("new line\n")

            mock_agent = MockAgent([])
            diff_handler = agent.tool_binding.wrap_tool(
                mock_agent,
                git_tool_module.git_diff,
            )

            # 测试基本 diff
            result = diff_handler()
            print(f"diff 结果: {result}")
            assert "new line" in result, f"期望包含 'new line'，实际：{result}"
            assert "hello.txt" in result

            # 测试 name_only
            result_no = diff_handler(name_only=True)
            print(f"name_only 结果: {result_no}")
            assert "hello.txt" in result_no
            assert "new line" not in result_no

            # 测试 stat
            result_stat = diff_handler(stat=True)
            print(f"stat 结果: {result_stat}")
            assert "hello.txt" in result_stat
            assert "1 insertion" in result_stat or "1 file changed" in result_stat

            # 测试 staged (暂存区应该为空)
            result_staged = diff_handler(staged=True)
            print(f"staged 结果: {result_staged}")
            assert "(无差异)" in result_staged

            # 测试 file_path 限定
            result_path = diff_handler(file_path="hello.txt")
            print(f"file_path 结果: {result_path}")
            assert "new line" in result_path

            # 测试非法 file_path（绝对路径）
            result_bad = diff_handler(file_path=os.path.abspath("/"))
            print(f"非法路径结果: {result_bad}")
            assert "错误" in result_bad

            print("✓ 测试通过")
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    test_basic_diff()
