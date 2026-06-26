#!/usr/bin/env python3
"""Cursor MCP 服务：将工具调用转发到运行中的 Godot 游戏 HTTP 服务。"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from godot_mcp.game_client import GameCommandError, send_command

mcp = FastMCP("godot-game")


def _format_result(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def game_command(
    port: int,
    command: str,
    data: dict[str, Any] | None = None,
    timeout_seconds: float = 30.0,
) -> str:
    """向指定端口的游戏实例发送协议命令。

    Args:
        port: launch_game 返回值中的 MCP 端口，或日志行 <<<ETHAN::GAME_MCP::HANDSHAKE::v1::port=XXXX>>> 或用户指定端口。
        command: 已在游戏侧 register_handle 注册的命令名。
        data: 传给 handle.on_receive 的载荷，不含 command 字段。
        timeout_seconds: 等待游戏回调 func_return 的最长时间（秒）。
    """
    try:
        result = send_command(
            port,
            command,
            data,
            timeout_seconds=timeout_seconds,
        )
    except GameCommandError as error:
        return f"错误: {error}"
    return _format_result(result)


if __name__ == "__main__":
    mcp.run()
