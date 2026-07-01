"""Godot 回归测试工具。"""

from __future__ import annotations

import pathlib
import sys

import agent.tool_binding

_EGENT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_EGENT_ROOT) not in sys.path:
    sys.path.append(str(_EGENT_ROOT))

from godot_test import format_exit_output, run_file  # noqa: E402


@agent.tool_binding.agent_tool(readonly=True)
def run_godot_test(script_path: str) -> str:
    """运行指定 GD 脚本的 run() 测试。

    @param script_path: GD 脚本路径（相对项目根或 res://）
    """
    exit_code, output = run_file(script_path.strip())
    return format_exit_output(exit_code, output)
