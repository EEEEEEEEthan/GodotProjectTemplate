"""运行 egent 自动化测试套件。"""

from __future__ import annotations

import importlib.util
import pathlib

import agent.tool_binding

_BUILTIN_ROOT = pathlib.Path(__file__).resolve().parent.parent

_run_all_tests_spec = importlib.util.spec_from_file_location(
    "run_all_tests", _BUILTIN_ROOT / "test" / "run_all_tests.py"
)
_run_all_tests = importlib.util.module_from_spec(_run_all_tests_spec)
_run_all_tests_spec.loader.exec_module(_run_all_tests)


def run_all(*, verbose: bool = False) -> tuple[bool, str]:
    """运行全部 test_*.py，返回 (是否全部通过, 汇总信息)。"""
    return _run_all_tests.run_all(verbose=verbose)


@agent.tool_binding.agent_tool(readonly=True)
def run_egent_test() -> str:
    """运行 addons/egent/builtin/test/ 下全部 test_*.py 测试套件，验证 egent 核心功能。

    覆盖 mcp_bridge、grep_search、file_edit、git、pylint、workflow、delete_file 等模块。
    """
    all_pass, summary = run_all(verbose=False)
    header = "全部通过" if all_pass else "存在失败"
    return f"egent 测试{header}：\n{summary}"
