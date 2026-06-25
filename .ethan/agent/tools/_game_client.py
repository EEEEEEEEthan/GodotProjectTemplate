"""向运行中的 Godot 游戏实例发送 HTTP 协议。"""

from __future__ import annotations

import json
import typing
import urllib.error
import urllib.request

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MCP_ROUTE = "/mcp"


class GameCommandError(RuntimeError):
    """游戏侧返回错误或 HTTP 失败。"""


def send_command(
    port: int,
    command: str,
    data: dict[str, typing.Any] | None = None,
    *,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
) -> dict[str, typing.Any]:
    payload = json.dumps(
        {
            "command": command,
            "data": data or {},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    url = f"http://{host}:{port}{MCP_ROUTE}"
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            response_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        response_text = error.read().decode("utf-8", errors="replace")
        raise GameCommandError(
            f"HTTP {error.code}：port={port}, command={command}, {response_text}"
        ) from error
    except urllib.error.URLError as error:
        reason = error.reason
        if "timed out" in str(reason).lower():
            raise GameCommandError(
                f"命令超时（{timeout_seconds}s）：port={port}, command={command}"
            ) from error
        raise GameCommandError(
            f"HTTP 请求失败：port={port}, command={command}, {reason}"
        ) from error

    try:
        body = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise GameCommandError(f"响应不是合法 JSON：{response_text}") from error

    if not isinstance(body, dict):
        raise GameCommandError(f"响应必须是 JSON 对象：{body}")

    if not body.get("ok", False):
        raise GameCommandError(str(body.get("error", "未知错误")))

    result = body.get("data", {})
    if not isinstance(result, dict):
        raise GameCommandError(f"data 字段必须是对象：{result}")
    return result
