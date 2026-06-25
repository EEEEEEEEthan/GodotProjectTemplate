"""向运行中 Godot 游戏 MCP HTTP 服务发送协议命令。"""

from __future__ import annotations

import importlib
import json
import typing

_game_client = importlib.import_module("agent.tools._game_client")
_output_util = importlib.import_module("agent.tools._output_util")


class GameCommandTool:
    """连接游戏 HTTP 服务并发送已注册协议。"""

    @staticmethod
    def send_command(
        command: str,
        data: dict[str, typing.Any] | None = None,
        *,
        port: int | None = None,
        host: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        """向游戏 MCP 服务发送协议并返回 JSON 结果。"""
        if not command or not command.strip():
            return "错误：command 不能为空。"
        resolved_port = (
            port
            if port is not None
            else _game_client.DEFAULT_PORT
        )
        if resolved_port <= 0:
            return "错误：port 必须是正整数。"
        resolved_host = (host or _game_client.DEFAULT_HOST).strip()

        try:
            result = _game_client.send_command(
                resolved_port,
                command.strip(),
                data,
                host=resolved_host or _game_client.DEFAULT_HOST,
                timeout_seconds=timeout_seconds,
            )
        except _game_client.GameCommandError as error:
            return f"错误：{error}"

        formatted = json.dumps(result, ensure_ascii=False, indent=2)
        return _output_util.truncate_output(formatted)
