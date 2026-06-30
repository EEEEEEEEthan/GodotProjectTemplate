"""Godot 回归测试工具。"""

from __future__ import annotations

import pathlib
import sys
import typing

_EGENT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_EGENT_ROOT) not in sys.path:
    sys.path.append(str(_EGENT_ROOT))

from godot_test import run_all, run_test_report  # noqa: E402


def run_godot_tests(
    agent_client: typing.Any,
    script_path: str | None = None,
    headless: bool = False,
) -> str:
    """运行 Godot 回归测试。不传 script_path 时运行 egent_handlers/tests 下全部 *_test.gd。

    @param script_path: GD 脚本路径（相对项目根或 res://），缺省运行全部
    @param headless: 无头模式，缺省 false
    """
    del agent_client
    if script_path and script_path.strip():
        _, info = run_test_report(script_path.strip(), headless=headless)
        return info
    _, info = run_all(headless=headless)
    return info
