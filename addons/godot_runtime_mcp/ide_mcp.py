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
    data: dict[str, Any],
    *,
    host: str = DEFAULT_HOST,
    timeout_seconds: float = 30.0,
) -> Any:
    """POST JSON payload to the given port; returns the response data field on success."""
    url = f"http://{host}:{port}/"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, json=data)
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
def send(port: int, data: dict[str, Any]) -> str:
    """Send a JSON command to a running Godot game instance.

    Args:
        port: Port from game log <<<GAME_MCP::PORT=XXXX>>>.
        data: Payload forwarded to the game-side command handler.
    """
    try:
        result = send_http(port, data)
    except GameCommandError as error:
        return f"error: {error}"
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()
