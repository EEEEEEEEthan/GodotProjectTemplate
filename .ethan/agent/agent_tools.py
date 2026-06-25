"""工具注册表：OpenAI function schema 与白名单过滤。"""

from __future__ import annotations

import collections.abc
import json
import typing

FULL_TOOL_LIST = [
    "skill_tool_learn_skill",
    "skill_tool_run_skill_script",
    "file_edit_tool_create_file",
    "file_edit_tool_apply_patch",
    "grep_search_tool_grep_search",
    "walk_files_tool_walk_files",
    "system_info_tool_system_info",
    "memory_tool_add_item",
    "memory_tool_remove_item",
    "memory_tool_update_item",
    "memory_tool_list_items",
    "memory_tool_find_str",
    "read_file_tool_read_file_outline_cs",
    "read_file_tool_read_file_outline_md",
    "read_file_tool_read_lines",
    "read_file_tool_read_whole_file",
]

__TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "skill_tool_learn_skill": {
        "type": "function",
        "function": {
            "name": "skill_tool_learn_skill",
            "description": "读取技能",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "技能id，与系统消息中列表一致",
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "相对技能根目录的文件路径，缺省表示 SKILL.md",
                    },
                },
                "required": ["skill_id"],
            },
        },
    },
    "skill_tool_run_skill_script": {
        "type": "function",
        "function": {
            "name": "skill_tool_run_skill_script",
            "description": "在 Agent 当前工作目录下执行技能包内脚本，标准输出与标准错误合并返回。使用脚本前请使用learn_skill工具阅读技能文档",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_id": {
                        "type": "string",
                        "description": "技能 id，与系统消息中列表一致",
                    },
                    "relative_path": {
                        "type": "string",
                        "description": "相对技能根目录的脚本文件路径",
                    },
                    "script_args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可选：按顺序传给脚本的命令行参数",
                    },
                },
                "required": ["skill_id", "relative_path"],
            },
        },
    },
    "file_edit_tool_create_file": {
        "type": "function",
        "function": {
            "name": "file_edit_tool_create_file",
            "description": "创建新文件，不覆盖已有文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "目标文件路径（相对工作目录，不接受绝对路径）",
                    },
                    "content": {
                        "type": "string",
                        "description": "文件初始内容，缺省创建空文件",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    "file_edit_tool_apply_patch": {
        "type": "function",
        "function": {
            "name": "file_edit_tool_apply_patch",
            "description": "替换文本",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "目标文件路径，可为绝对路径或相对当前工作目录",
                    },
                    "old_text": {
                        "type": "string",
                        "description": "要被替换的原文片段，须在文件中出现且仅出现一次",
                    },
                    "new_text": {
                        "type": "string",
                        "description": "替换后的内容",
                    },
                },
                "required": ["file_path", "old_text"],
            },
        },
    },
    "grep_search_tool_grep_search": {
        "type": "function",
        "function": {
            "name": "grep_search_tool_grep_search",
            "description": "在工作区内用正则全目录搜索文件内容。用于查找符号引用、字符串、模式匹配等；取得行号后可配合 read_lines 阅读上下文",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "正则表达式（搜索每行内容）",
                    },
                    "directory": {
                        "type": "string",
                        "description": "搜索根目录（相对工作目录），缺省 .",
                    },
                    "filter": {
                        "type": "string",
                        "description": "文件名通配符（fnmatch），缺省 *",
                    },
                    "ignore_case": {
                        "type": "boolean",
                        "description": "忽略大小写",
                    },
                    "max_matches": {
                        "type": "integer",
                        "description": "最多输出匹配行数，缺省 500",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    "walk_files_tool_walk_files": {
        "type": "function",
        "function": {
            "name": "walk_files_tool_walk_files",
            "description": "遍历目录文件树并缩进输出文件名。用于了解项目结构、列出目录下文件",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {
                        "type": "string",
                        "description": "要遍历的目录（相对工作目录）",
                    },
                    "filter": {
                        "type": "string",
                        "description": "文件与文件夹名通配符，缺省 *",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "最大层级深度，0 表示不限制，缺省 1",
                    },
                },
                "required": ["directory"],
            },
        },
    },
    "system_info_tool_system_info": {
        "type": "function",
        "function": {
            "name": "system_info_tool_system_info",
            "description": "获取当前时间、时区、操作系统与运行环境属性",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    "memory_tool_add_item": {
        "type": "function",
        "function": {
            "name": "memory_tool_add_item",
            "description": "添加长期记忆条目。标题为唯一键（大小写不敏感）",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆标题"},
                    "value": {"type": "string", "description": "记忆正文"},
                },
                "required": ["key", "value"],
            },
        },
    },
    "memory_tool_remove_item": {
        "type": "function",
        "function": {
            "name": "memory_tool_remove_item",
            "description": "删除长期记忆条目",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆标题"},
                },
                "required": ["key"],
            },
        },
    },
    "memory_tool_update_item": {
        "type": "function",
        "function": {
            "name": "memory_tool_update_item",
            "description": "更新长期记忆条目",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "记忆标题"},
                    "value": {"type": "string", "description": "更新后的记忆正文"},
                },
                "required": ["key", "value"],
            },
        },
    },
    "memory_tool_list_items": {
        "type": "function",
        "function": {
            "name": "memory_tool_list_items",
            "description": "列出长期记忆条目，可按标题正则筛选。每次对话开始建议先查询相关记忆",
            "parameters": {
                "type": "object",
                "properties": {
                    "filter": {
                        "type": "string",
                        "description": "可选：标题筛选正则，忽略大小写",
                    },
                },
            },
        },
    },
    "memory_tool_find_str": {
        "type": "function",
        "function": {
            "name": "memory_tool_find_str",
            "description": "在记忆标题与正文中正则搜索（忽略大小写）",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "搜索用正则表达式",
                    },
                },
                "required": ["pattern"],
            },
        },
    },
    "read_file_tool_read_file_outline_cs": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_file_outline_cs",
            "description": "读取 C# 源文件大纲（namespace / 类型 / 成员）。阅读 .cs 文件时先读大纲",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "C# 源文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    "read_file_tool_read_file_outline_md": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_file_outline_md",
            "description": "读取 Markdown 文件标题大纲。阅读 .md 文件时先读大纲",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Markdown 文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    "read_file_tool_read_lines": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_lines",
            "description": "按行号范围读取文件片段（1-based，含首尾）。通常在 grep_search 或大纲取得行号后使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对工作目录）",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "起始行号（1-based，含）",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "结束行号（1-based，含）",
                    },
                },
                "required": ["file_path", "start_line", "end_line"],
            },
        },
    },
    "read_file_tool_read_whole_file": {
        "type": "function",
        "function": {
            "name": "read_file_tool_read_whole_file",
            "description": "读取文件全文。用于非 .cs/.md 文件，或大纲策略无法定位细节时的 fallback",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（相对工作目录）",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
}


def select_advertised_tools(whitelist: list[str]) -> list[dict[str, typing.Any]]:
    """按白名单筛选 OpenAI tools schema。"""
    allowed = set(whitelist)
    return [
        __TOOL_SCHEMAS[name]
        for name in FULL_TOOL_LIST
        if name in allowed
    ]


def resolve_tool_name(openai_name: str) -> str | None:
    """校验 OpenAI function name 是否为已注册工具名。"""
    if openai_name in __TOOL_SCHEMAS:
        return openai_name
    return None


ToolHandler = typing.Callable[..., str | collections.abc.Awaitable[str]]


def build_tool_dispatch(
    handlers: dict[str, ToolHandler],
) -> typing.Callable[[str, dict[str, typing.Any]], collections.abc.Awaitable[str]]:
    """构建 OpenAI 工具名到 handler 的异步分发函数。"""
    async def invoke(openai_name: str, arguments: dict[str, typing.Any]) -> str:
        tool_name = resolve_tool_name(openai_name)
        if tool_name is None:
            allowed_tools = "、".join(FULL_TOOL_LIST)
            return (
                f"错误：未知工具 {openai_name}。"
                f"请使用 {allowed_tools}。"
            )
        handler = handlers.get(tool_name)
        if handler is None:
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


def parse_tool_arguments(arguments_text: str) -> dict[str, typing.Any]:
    """解析 LLM 返回的工具参数 JSON。"""
    if not arguments_text:
        return {}
    try:
        parsed = json.loads(arguments_text)
    except json.JSONDecodeError as exception:
        return {"__parse_error__": str(exception)}
    return parsed if isinstance(parsed, dict) else {}
