"""工具方法绑定：从签名与 @param 文档生成 OpenAI schema。"""

from __future__ import annotations

import collections.abc
import dataclasses
import inspect
import re
import types
import typing

ToolHandler = typing.Callable[..., str | collections.abc.Awaitable[str]]

_PARAM_LINE = re.compile(r"^@param\s+(\w+)\s*:\s*(.+)$")
_TOOL_NAME_LINE = re.compile(r"^@tool_name\s+(\S+)\s*$")
_ENUM_LINE = re.compile(r"^@enum\s+(\w+)\s*:\s*(.+)$")

BUILTIN_TOOL_NAMES: tuple[str, ...] = (
    "skill_tool_learn_skill",
    "skill_tool_run_skill_script",
    "file_edit_tool_create_file",
    "file_edit_tool_apply_patch",
    "grep_search_tool_grep_search",
    "walk_files_tool_walk_files",
    "system_info_tool_system_info",
    "fuck_tool_fuck",
    "memory_tool_add_item",
    "memory_tool_remove_item",
    "memory_tool_update_item",
    "memory_tool_list_items",
    "memory_tool_find_str",
    "read_file_tool_read_file_outline_cs",
    "read_file_tool_read_file_outline_md",
    "read_file_tool_read_file_outline_py",
    "read_file_tool_read_lines",
    "read_file_tool_read_whole_file",
    "launch_game_tool_launch_game",
    "shell_tool_exec",
    "shell_tool_bg_exec",
    "shell_tool_bg_status",
    "shell_tool_wait",
)


@dataclasses.dataclass(frozen=True)
class ParsedToolDoc:
    summary: str
    tool_name: str | None
    param_descriptions: dict[str, str]
    param_enums: dict[str, list[str]]


@dataclasses.dataclass(frozen=True)
class ToolBinding:
    name: str
    handler: ToolHandler
    schema: dict[str, typing.Any]


def tool(
    *,
    name: str | None = None,
    description: str | None = None,
) -> typing.Callable[[ToolHandler], ToolHandler]:
    """可选覆盖工具名与描述。"""

    def decorator(handler: ToolHandler) -> ToolHandler:
        if name is not None:
            handler.__tool_name__ = name  # type: ignore[attr-defined]
        if description is not None:
            handler.__tool_description__ = description  # type: ignore[attr-defined]
        return handler

    return decorator


def bind_tools(*handlers: ToolHandler) -> dict[str, ToolBinding]:
    """将工具方法列表绑定为 name → ToolBinding 映射。"""
    bindings: dict[str, ToolBinding] = {}
    for handler in handlers:
        binding = build_binding(handler)
        bindings[binding.name] = binding
    return bindings


def build_binding(handler: ToolHandler) -> ToolBinding:
    """为单个工具方法构建绑定（含缓存 schema）。"""
    cache = getattr(handler, "__tool_binding_cache__", None)
    if isinstance(cache, ToolBinding):
        return cache
    name = resolve_tool_name(handler)
    schema = build_openai_schema(handler, name)
    binding = ToolBinding(name=name, handler=handler, schema=schema)
    try:
        handler.__tool_binding_cache__ = binding  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        pass
    return binding


def to_openai_tools(bindings: dict[str, ToolBinding]) -> list[dict[str, typing.Any]]:
    """按工具名排序输出 OpenAI tools 列表。"""
    return [bindings[name].schema for name in sorted(bindings)]


def select_bindings(
    all_bindings: dict[str, ToolBinding],
    whitelist: collections.abc.Iterable[str],
) -> dict[str, ToolBinding]:
    """按白名单筛选绑定。"""
    allowed = set(whitelist)
    return {
        name: binding
        for name, binding in all_bindings.items()
        if name in allowed
    }


def merge_advertised_tools(
    bindings: dict[str, ToolBinding],
    extra_schemas: dict[str, dict[str, typing.Any]] | None = None,
    whitelist: collections.abc.Iterable[str] | None = None,
) -> list[dict[str, typing.Any]]:
    """合并内置工具 schema 与 MCP 等额外 schema。"""
    allowed = set(whitelist) if whitelist is not None else None
    schemas = [
        binding.schema
        for name, binding in sorted(bindings.items())
        if allowed is None or name in allowed
    ]
    if extra_schemas:
        for name, schema in sorted(extra_schemas.items()):
            if allowed is not None and name not in allowed:
                continue
            if name not in bindings:
                schemas.append(schema)
    return schemas


async def invoke_handler(handler: ToolHandler, arguments: dict[str, typing.Any]) -> str:
    """调用工具方法并规范化返回值为字符串。"""
    if "__parse_error__" in arguments:
        return f"错误：工具参数 JSON 无效：{arguments['__parse_error__']}"
    try:
        result = handler(**arguments)
    except TypeError as exception:
        tool_name = resolve_tool_name(handler)
        return f"错误：工具参数无效（{tool_name}）：{exception}"
    if inspect.isawaitable(result):
        result = await result
    return str(result)


def resolve_tool_name(handler: ToolHandler) -> str:
    """解析 OpenAI function 名。"""
    explicit = getattr(handler, "__tool_name__", None)
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    parsed = parse_tool_docstring(inspect.getdoc(handler))
    if parsed.tool_name:
        return parsed.tool_name
    method_name = _unwrap_callable(handler).__name__
    owner_class = _resolve_owner_class_name(handler)
    if owner_class:
        return f"{_class_to_snake(owner_class)}_{method_name}"
    return method_name


def build_openai_schema(handler: ToolHandler, tool_name: str) -> dict[str, typing.Any]:
    """从方法签名与文档构建 OpenAI function schema。"""
    parsed = parse_tool_docstring(inspect.getdoc(handler))
    override_description = getattr(handler, "__tool_description__", None)
    description = (
        override_description.strip()
        if isinstance(override_description, str) and override_description.strip()
        else parsed.summary
    )
    callable_target = _unwrap_callable(handler)
    signature = inspect.signature(callable_target)
    type_hints = typing.get_type_hints(
        callable_target,
        include_extras=True,
    )
    properties: dict[str, typing.Any] = {}
    required: list[str] = []
    for parameter_name, parameter in signature.parameters.items():
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if parameter_name in {"self", "cls"}:
            continue
        property_schema = _hint_to_json_schema(type_hints.get(parameter_name, str))
        param_description = parsed.param_descriptions.get(parameter_name)
        if param_description:
            property_schema = dict(property_schema)
            property_schema["description"] = param_description
        enum_values = parsed.param_enums.get(parameter_name)
        if enum_values:
            property_schema = dict(property_schema)
            property_schema["type"] = "string"
            property_schema["enum"] = enum_values
        properties[parameter_name] = property_schema
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter_name)
    parameters: dict[str, typing.Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        parameters["required"] = required
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": description,
            "parameters": parameters,
        },
    }


def parse_tool_docstring(documentation: str | None) -> ParsedToolDoc:
    """解析 @param / @tool_name / @enum 文档块。"""
    if not documentation:
        return ParsedToolDoc("", None, {}, {})
    summary_lines: list[str] = []
    param_descriptions: dict[str, str] = {}
    param_enums: dict[str, list[str]] = {}
    tool_name: str | None = None
    for raw_line in documentation.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        param_match = _PARAM_LINE.match(stripped)
        if param_match:
            param_descriptions[param_match.group(1)] = param_match.group(2).strip()
            continue
        tool_name_match = _TOOL_NAME_LINE.match(stripped)
        if tool_name_match:
            tool_name = tool_name_match.group(1)
            continue
        enum_match = _ENUM_LINE.match(stripped)
        if enum_match:
            param_enums[enum_match.group(1)] = [
                value.strip()
                for value in enum_match.group(2).split(",")
                if value.strip()
            ]
            continue
        if stripped.startswith("@"):
            continue
        if not param_descriptions and not tool_name and not param_enums:
            summary_lines.append(stripped)
    return ParsedToolDoc(
        summary=" ".join(summary_lines).strip(),
        tool_name=tool_name,
        param_descriptions=param_descriptions,
        param_enums=param_enums,
    )


def _unwrap_callable(handler: ToolHandler) -> typing.Callable[..., typing.Any]:
    target = handler
    if inspect.ismethod(target):
        target = target.__func__
    while isinstance(target, (classmethod, staticmethod)):
        target = target.__func__
    return target


def _resolve_owner_class_name(handler: ToolHandler) -> str:
    if inspect.ismethod(handler):
        return handler.__self__.__class__.__name__
    qualname = getattr(handler, "__qualname__", "")
    if "." in qualname:
        return qualname.rsplit(".", 1)[0]
    return ""


def _class_to_snake(class_name: str) -> str:
    if not class_name:
        return ""
    characters: list[str] = []
    for index, character in enumerate(class_name):
        if character.isupper() and index > 0:
            previous = class_name[index - 1]
            next_character = class_name[index + 1] if index + 1 < len(class_name) else ""
            if previous.islower() or (next_character and next_character.islower()):
                characters.append("_")
        characters.append(character.lower())
    return "".join(characters)


def _hint_to_json_schema(hint: typing.Any) -> dict[str, typing.Any]:
    if hint is inspect.Parameter.empty:
        return {"type": "string"}
    origin = typing.get_origin(hint)
    if origin is typing.Union or origin is types.UnionType:
        arguments = typing.get_args(hint)
        non_none = [item for item in arguments if item is not type(None)]
        if len(non_none) == 1:
            return _hint_to_json_schema(non_none[0])
    if origin is list:
        item_hint = typing.get_args(hint)[0] if typing.get_args(hint) else str
        return {"type": "array", "items": _hint_to_json_schema(item_hint)}
    if origin is dict:
        return {"type": "object"}
    if origin is typing.Literal:
        literal_values = typing.get_args(hint)
        if literal_values and all(isinstance(value, str) for value in literal_values):
            return {"type": "string", "enum": list(literal_values)}
    if hint in (str, typing.Text):
        return {"type": "string"}
    if hint is int:
        return {"type": "integer"}
    if hint is float:
        return {"type": "number"}
    if hint is bool:
        return {"type": "boolean"}
    return {"type": "string"}
