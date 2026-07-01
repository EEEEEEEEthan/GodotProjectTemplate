"""Cursor MCP stdio 入口，经 HTTP 与运行中游戏通信。"""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_HOST = "127.0.0.1"

mcp = FastMCP("godot-game")


class GameCommandError(RuntimeError):
    """游戏侧返回错误或 HTTP 失败。"""


def send_http(
    port: int,
    data: dict[str, Any],
    *,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
) -> Any:
    """向指定端口 POST JSON 载荷，成功时返回响应 data 字段。"""
    url = f"http://{host}:{port}/"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=data)
            response.raise_for_status()
    except httpx.TimeoutException as error:
        raise GameCommandError(
            f"请求超时（{timeout_seconds}s）：port={port}"
        ) from error
    except httpx.HTTPError as error:
        raise GameCommandError(f"HTTP 请求失败：port={port}, {error}") from error

    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise GameCommandError(f"响应不是合法 JSON：{response.text}") from error

    if not isinstance(body, dict):
        raise GameCommandError(f"响应必须是 JSON 对象：{body}")

    if not body.get("ok", False):
        raise GameCommandError(str(body.get("error", "未知错误")))

    return body.get("data", "")


@mcp.tool()
def send(port: int, data: dict[str, Any]) -> str:
    """向运行中的 Godot 游戏实例发送 JSON 指令。

    Args:
        port: 游戏日志 <<<EGENT::GAME_MCP::HANDSHAKE::v1::port=XXXX>>> 中的端口。
        data: 发给游戏侧 command_received 信号的载荷。
    """
    try:
        result = send_http(port, data)
    except GameCommandError as error:
        return f"错误: {error}"
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
