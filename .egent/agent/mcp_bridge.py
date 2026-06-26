"""MCP 客户端桥接：连接 stdio MCP 服务并将工具暴露给 Agent。"""

from __future__ import annotations

import contextlib
import dataclasses
import os
import pathlib
import sys
import typing

import anyio

import mcp.types
import mcp.client.stdio
import mcp.client.session
import mcp.shared.exceptions

import agent.builtin_tools._output_util as output_util


MCP_TOOL_PREFIX = "mcp__"


@dataclasses.dataclass(frozen=True)
class McpServerConfig:
    """单个 MCP 服务的启动参数。"""

    command: str
    args: list[str]
    cwd: str | None = None
    env: dict[str, str] | None = None


@dataclasses.dataclass(frozen=True)
class McpToolBinding:
    """OpenAI 工具名与 MCP 会话的映射。"""

    openai_name: str
    server_id: str
    tool_name: str
    schema: dict[str, typing.Any]


class McpBridge:
    """管理 MCP 连接、工具发现与调用。"""

    def __init__(self, servers: dict[str, McpServerConfig]) -> None:
        self.__servers = dict(servers)
        self.__exit_stack = contextlib.AsyncExitStack()
        self.__sessions: dict[str, mcp.client.session.ClientSession] = {}
        self.__bindings: dict[str, McpToolBinding] = {}
        self.__started = False

    @property
    def bindings(self) -> dict[str, McpToolBinding]:
        """已发现的 MCP 工具绑定。"""
        return dict(self.__bindings)

    async def start(self) -> None:
        """启动全部 MCP 服务并完成工具发现。"""
        if self.__started:
            return
        project_root = pathlib.Path.cwd()
        for server_id, server_config in self.__servers.items():
            await self.__connect_server(project_root, server_id, server_config)
        self.__started = True

    async def close(self) -> None:
        """关闭全部 MCP 连接。"""
        await self.__exit_stack.aclose()
        self.__sessions.clear()
        self.__bindings.clear()
        self.__started = False

    def all_schemas(self) -> dict[str, dict[str, typing.Any]]:
        """返回全部已发现 MCP 工具的 OpenAI schema。"""
        return {
            name: binding.schema
            for name, binding in self.__bindings.items()
        }

    async def invoke(
        self,
        openai_name: str,
        arguments: dict[str, typing.Any],
    ) -> str:
        """调用 MCP 工具并返回文本结果。"""
        binding = self.__bindings.get(openai_name)
        if binding is None:
            return f"错误：未找到 MCP 工具 {openai_name}"
        session = self.__sessions.get(binding.server_id)
        if session is None:
            return f"错误：MCP 服务未连接 {binding.server_id}"

        try:
            result = await session.call_tool(binding.tool_name, arguments=arguments)
        except (
            mcp.shared.exceptions.McpError,
            RuntimeError,
            anyio.ClosedResourceError,
            anyio.BrokenResourceError,
            OSError,
        ) as error:
            return f"错误：MCP 调用失败（{openai_name}）：{error}"

        return output_util.truncate_output(format_call_tool_result(result))

    async def __connect_server(
        self,
        project_root: pathlib.Path,
        server_id: str,
        server_config: McpServerConfig,
    ) -> None:
        server_parameters = build_stdio_server_parameters(
            project_root,
            server_config,
        )
        read_stream, write_stream = await self.__exit_stack.enter_async_context(
            mcp.client.stdio.stdio_client(server_parameters),
        )
        session = await self.__exit_stack.enter_async_context(
            mcp.client.session.ClientSession(read_stream, write_stream),
        )
        await session.initialize()
        self.__sessions[server_id] = session

        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            openai_name = build_mcp_openai_tool_name(server_id, tool.name)
            self.__bindings[openai_name] = McpToolBinding(
                openai_name=openai_name,
                server_id=server_id,
                tool_name=tool.name,
                schema=convert_mcp_tool_schema(openai_name, tool),
            )


def parse_mcp_servers(config: dict[str, typing.Any]) -> dict[str, McpServerConfig]:
    """从 mcp.json 的 mcpServers 字段解析 MCP 配置。"""
    raw_servers = config.get("mcpServers")
    if not isinstance(raw_servers, dict):
        return {}

    servers: dict[str, McpServerConfig] = {}
    for server_id, raw_entry in raw_servers.items():
        if not isinstance(server_id, str) or not isinstance(raw_entry, dict):
            continue
        command = raw_entry.get("command")
        if not isinstance(command, str) or not command.strip():
            continue
        raw_args = raw_entry.get("args")
        args = (
            [item for item in raw_args if isinstance(item, str)]
            if isinstance(raw_args, list)
            else []
        )
        raw_cwd = raw_entry.get("cwd")
        cwd = raw_cwd if isinstance(raw_cwd, str) and raw_cwd.strip() else None
        raw_env = raw_entry.get("env")
        env = (
            {key: value for key, value in raw_env.items() if isinstance(value, str)}
            if isinstance(raw_env, dict)
            else None
        )
        servers[server_id.strip()] = McpServerConfig(
            command=command.strip(),
            args=args,
            cwd=cwd,
            env=env,
        )
    return servers


def build_mcp_openai_tool_name(server_id: str, tool_name: str) -> str:
    """生成 Agent 侧 OpenAI 工具名。"""
    return f"{MCP_TOOL_PREFIX}{server_id}__{tool_name}"


def parse_mcp_openai_tool_name(openai_name: str) -> tuple[str, str] | None:
    """解析 OpenAI 工具名为 (server_id, tool_name)。"""
    if not openai_name.startswith(MCP_TOOL_PREFIX):
        return None
    remainder = openai_name[len(MCP_TOOL_PREFIX) :]
    server_id, separator, tool_name = remainder.partition("__")
    if not separator or not server_id or not tool_name:
        return None
    return server_id, tool_name


def convert_mcp_tool_schema(
    openai_name: str,
    tool: mcp.types.Tool,
) -> dict[str, typing.Any]:
    """将 MCP Tool 转为 OpenAI function schema。"""
    parameters = tool.inputSchema
    if not isinstance(parameters, dict):
        parameters = {"type": "object", "properties": {}}
    description = tool.description or f"MCP 工具 {tool.name}"
    return {
        "type": "function",
        "function": {
            "name": openai_name,
            "description": description,
            "parameters": parameters,
        },
    }


def format_call_tool_result(result: mcp.types.CallToolResult) -> str:
    """格式化 MCP call_tool 返回内容。"""
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, mcp.types.TextContent):
            parts.append(block.text)
        else:
            parts.append(str(block))
    text = "\n".join(part for part in parts if part)
    if result.isError:
        return f"错误：{text or 'MCP 工具返回错误'}"
    return text or "(空结果)"


def build_stdio_server_parameters(
    project_root: pathlib.Path,
    server_config: McpServerConfig,
) -> mcp.client.stdio.StdioServerParameters:
    """构建 stdio MCP 服务启动参数。"""
    command = server_config.command
    if command.strip().lower() in {"python", "python3", "py"}:
        command = sys.executable

    resolved_args = [
        resolve_launch_argument(project_root, argument)
        for argument in server_config.args
    ]
    working_directory = server_config.cwd
    if working_directory is None and resolved_args:
        script_path = pathlib.Path(resolved_args[0])
        if script_path.suffix == ".py":
            working_directory = os.fspath(script_path.parent)
    elif working_directory is not None:
        working_directory = resolve_project_path(project_root, working_directory)

    return mcp.client.stdio.StdioServerParameters(
        command=command,
        args=resolved_args,
        cwd=working_directory,
        env=server_config.env,
    )


def resolve_launch_argument(project_root: pathlib.Path, argument: str) -> str:
    """解析启动参数：仅对路径类参数做项目根相对解析。"""
    if argument.startswith("-"):
        return argument
    path = pathlib.Path(argument)
    if (
        path.is_absolute()
        or argument.startswith(".")
        or "/" in argument
        or "\\" in argument
        or path.suffix == ".py"
    ):
        return resolve_project_path(project_root, argument)
    return argument


def resolve_project_path(project_root: pathlib.Path, value: str) -> str:
    """将相对路径解析为绝对路径字符串。"""
    path = pathlib.Path(value)
    if path.is_absolute():
        return os.fspath(path)
    return os.fspath((project_root / path).resolve())
