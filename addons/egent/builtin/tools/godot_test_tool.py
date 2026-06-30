"""Godot 回归测试工具。"""

from __future__ import annotations

import pathlib
import sys
import typing

_EGENT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_EGENT_ROOT) not in sys.path:
    sys.path.append(str(_EGENT_ROOT))

from godot_test import run_file  # noqa: E402


def run_godot_test(agent_client: typing.Any, script_path: str) -> str:
    """运行指定 GD 脚本的 run() 测试。

    @param script_path: GD 脚本路径（相对项目根或 res://）
    """
    del agent_client
    return run_file(script_path.strip())
