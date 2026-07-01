"""Cursor MCP stdio entry point; communicates with a running game over HTTP."""

from __future__ import annotations

import json
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

DEFAULT_HOST = "127.0.0.1"

mcp = FastMCP("godot-game")


class GameCommandError(RuntimeError):
    """Game-side error response or HTTP failure."""


def send_http(
    port: int,
    script: str,
    *,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
) -> Any:
    """POST GDScript source to the given port; returns the response data field on success."""
    url = f"http://{host}:{port}/"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(
                url,
                content=script.encode("utf-8"),
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
            response.raise_for_status()
    except httpx.TimeoutException as error:
        raise GameCommandError(
            f"request timed out ({timeout_seconds}s): port={port}"
        ) from error
    except httpx.HTTPError as error:
        raise GameCommandError(f"HTTP request failed: port={port}, {error}") from error

    try:
        body = response.json()
    except json.JSONDecodeError as error:
        raise GameCommandError(f"response is not valid JSON: {response.text}") from error

    if not isinstance(body, dict):
        raise GameCommandError(f"response must be a JSON object: {body}")

    if not body.get("ok", False):
        raise GameCommandError(str(body.get("error", "unknown error")))

    return body.get("data", "")


@mcp.tool()
def run(port: int, script: str) -> str:
    """在运行中的 Godot 实例里执行 GDScript。

    Args:
        port: 游戏日志 <<<GAME_MCP::PORT=XXXX>>> 中的端口号。
        script: 完整 GDScript 源码，须 extends RefCounted 并定义 run(scene_tree) 方法。
    """
    try:
        result = send_http(port, script)
    except GameCommandError as error:
        return f"error: {error}"
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
