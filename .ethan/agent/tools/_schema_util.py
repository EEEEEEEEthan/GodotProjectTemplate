"""OpenAI function tool schema 构建辅助。"""

from __future__ import annotations

import typing

SchemaProperty = dict[str, typing.Any]
SchemaProperties = dict[str, SchemaProperty]


def object_parameters(
    properties: SchemaProperties,
    *,
    required: list[str] | None = None,
) -> dict[str, typing.Any]:
    """构造 parameters 对象。"""
    parameters: dict[str, typing.Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters["required"] = required
    return parameters


def file_path_property(description: str) -> SchemaProperty:
    """file_path 参数字段。"""
    return {"type": "string", "description": description}


def pattern_property(description: str) -> SchemaProperty:
    """pattern 参数字段。"""
    return {"type": "string", "description": description}


def function_schema(
    name: str,
    description: str,
    properties: SchemaProperties,
    *,
    required: list[str] | None = None,
) -> dict[str, typing.Any]:
    """构造单条 function tool schema。"""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": object_parameters(properties, required=required),
        },
    }
