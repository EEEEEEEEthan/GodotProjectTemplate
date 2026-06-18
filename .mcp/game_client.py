"""向运行中的 Godot 游戏实例发送 HTTP 指令。"""

from __future__ import annotations

import json
from typing import Any

import httpx

DEFAULT_HOST = "127.0.0.1"
MCP_ROUTE = "/mcp"


class GameCommandError(RuntimeError):
    """游戏侧返回错误或 HTTP 失败。"""


def send_command(
    port: int,
    command: str,
    data: dict[str, Any] | None = None,
    *,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
) -> dict[str, Any]:
    payload = {
        "command": command,
        "data": data or {},
    }
    url = f"http://{host}:{port}{MCP_ROUTE}"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
    except httpx.TimeoutException as error:
        raise GameCommandError(
            f"命令超时（{timeout_seconds}s）：port={port}, command={command}"
        ) from error
    except httpx.HTTPError as error:
        raise GameCommandError(
            f"HTTP 请求失败：port={port}, command={command}, {error}"
        ) from error

    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise GameCommandError(f"响应不是合法 JSON：{response.text}") from error

    if not isinstance(body, dict):
        raise GameCommandError(f"响应必须是 JSON 对象：{body}")

    if not body.get("ok", False):
        raise GameCommandError(str(body.get("error", "未知错误")))

    result = body.get("data", {})
    if not isinstance(result, dict):
        raise GameCommandError(f"data 字段必须是对象：{result}")
    return result
