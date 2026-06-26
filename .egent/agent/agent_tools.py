"""工具调用辅助：参数格式化与分发。"""

from __future__ import annotations

import collections.abc
import json
import typing

import agent.tool_binding

ToolHandler = agent.tool_binding.ToolHandler


def build_tool_dispatch(
    bindings: dict[str, agent.tool_binding.ToolBinding],
    *,
    extra_schemas: dict[str, dict[str, typing.Any]] | None = None,
    mcp_invoke: typing.Callable[
        [str, dict[str, typing.Any]],
        collections.abc.Awaitable[str],
    ] | None = None,
) -> typing.Callable[[str, dict[str, typing.Any]], collections.abc.Awaitable[str]]:
    """构建 OpenAI 工具名到 handler 的异步分发函数。"""

    async def invoke(openai_name: str, arguments: dict[str, typing.Any]) -> str:
        binding = bindings.get(openai_name)
        if binding is not None:
            return await agent.tool_binding.invoke_handler(binding.handler, arguments)
        if mcp_invoke is not None and openai_name in (extra_schemas or {}):
            try:
                if "__parse_error__" in arguments:
                    return f"错误：工具参数 JSON 无效：{arguments['__parse_error__']}"
                return await mcp_invoke(openai_name, arguments)
            except TypeError as exception:
                return f"错误：工具参数无效（{openai_name}）：{exception}"
        allowed_tools = "、".join({*bindings, *(extra_schemas or {})})
        return (
            f"错误：未知工具 {openai_name}。"
            f"请使用 {allowed_tools}。"
        )

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
