"""工具注册表：OpenAI function schema 与白名单过滤。"""

from __future__ import annotations

import collections.abc
import json
import typing

import agent.tools.file_edit_tool as file_edit_tool
import agent.tools.fuck_tool as fuck_tool
import agent.tools.grep_search_tool as grep_search_tool
import agent.tools.launch_game_tool as launch_game_tool
import agent.tools.memory_tool as memory_tool
import agent.tools.read_file_tool as read_file_tool
import agent.tools.shell_tool as shell_tool
import agent.tools.skill_tool as skill_tool
import agent.tools.system_info_tool as system_info_tool
import agent.tools.walk_files_tool as walk_files_tool
TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    **skill_tool.TOOL_SCHEMAS,
    **file_edit_tool.TOOL_SCHEMAS,
    **fuck_tool.TOOL_SCHEMAS,
    **grep_search_tool.TOOL_SCHEMAS,
    **walk_files_tool.TOOL_SCHEMAS,
    **system_info_tool.TOOL_SCHEMAS,
    **memory_tool.TOOL_SCHEMAS,
    **read_file_tool.TOOL_SCHEMAS,
    **launch_game_tool.TOOL_SCHEMAS,
    **shell_tool.TOOL_SCHEMAS,
}


def select_advertised_tools(
    whitelist: list[str],
    extra_schemas: dict[str, dict[str, typing.Any]] | None = None,
) -> list[dict[str, typing.Any]]:
    """按白名单筛选 OpenAI tools schema。"""
    allowed = set(whitelist)
    all_schemas = dict(TOOL_SCHEMAS)
    if extra_schemas:
        all_schemas.update(extra_schemas)
    return [
        all_schemas[name]
        for name in all_schemas
        if name in allowed
    ]


def resolve_tool_name(
    openai_name: str,
    extra_schemas: dict[str, dict[str, typing.Any]] | None = None,
) -> str | None:
    """校验 OpenAI function name 是否为已注册工具名。"""
    if openai_name in TOOL_SCHEMAS:
        return openai_name
    if extra_schemas and openai_name in extra_schemas:
        return openai_name
    return None


ToolHandler = typing.Callable[..., str | collections.abc.Awaitable[str]]


def build_tool_dispatch(
    handlers: dict[str, ToolHandler],
    *,
    extra_schemas: dict[str, dict[str, typing.Any]] | None = None,
    mcp_invoke: typing.Callable[
        [str, dict[str, typing.Any]],
        collections.abc.Awaitable[str],
    ] | None = None,
) -> typing.Callable[[str, dict[str, typing.Any]], collections.abc.Awaitable[str]]:
    """构建 OpenAI 工具名到 handler 的异步分发函数。"""
    async def invoke(openai_name: str, arguments: dict[str, typing.Any]) -> str:
        tool_name = resolve_tool_name(openai_name, extra_schemas)
        if tool_name is None:
            allowed_tools = "、".join({*TOOL_SCHEMAS, *(extra_schemas or {})})
            return (
                f"错误：未知工具 {openai_name}。"
                f"请使用 {allowed_tools}。"
            )
        handler = handlers.get(tool_name)
        if handler is None:
            if mcp_invoke is not None and openai_name.startswith("mcp__"):
                try:
                    if "__parse_error__" in arguments:
                        return f"错误：工具参数 JSON 无效：{arguments['__parse_error__']}"
                    return await mcp_invoke(openai_name, arguments)
                except TypeError as exception:
                    return f"错误：工具参数无效（{tool_name}）：{exception}"
            return f"错误：工具未注册 {tool_name}"
        try:
            if "__parse_error__" in arguments:
                return f"错误：工具参数 JSON 无效：{arguments['__parse_error__']}"
            result = handler(**arguments)
        except TypeError as exception:
            return f"错误：工具参数无效（{tool_name}）：{exception}"
        if hasattr(result, "__await__"):
            result = await result
        return str(result)

    return invoke


def format_tool_arguments(arguments: dict[str, typing.Any]) -> str:
    """将工具参数字典格式化为可读字符串。"""
    if not arguments:
        return ""
    return ", ".join(
        f"{key}={value}"
        for key, value in arguments.items()
        if key != "__parse_error__"
    )


def format_tool_arguments_brief(
    arguments: dict[str, typing.Any],
    *,
    max_value_length: int = 80,
) -> str:
    """将工具参数格式化为简短摘要，长值截断。"""
    if not arguments:
        return ""
    parts: list[str] = []
    for key, value in arguments.items():
        if key == "__parse_error__":
            continue
        if isinstance(value, str):
            text = value
        elif isinstance(value, (dict, list)):
            text = json.dumps(value, ensure_ascii=False)
        else:
            text = repr(value)
        if len(text) > max_value_length:
            text = f"{text[:max_value_length]}..."
        parts.append(f"{key}={text}")
    return ", ".join(parts)


def parse_tool_arguments(arguments_text: str) -> dict[str, typing.Any]:
    """解析 LLM 返回的工具参数 JSON。"""
    if not arguments_text:
        return {}
    try:
        parsed = json.loads(arguments_text)
    except json.JSONDecodeError as exception:
        return {"__parse_error__": str(exception)}
    return parsed if isinstance(parsed, dict) else {}
