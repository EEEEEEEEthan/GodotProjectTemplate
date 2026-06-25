"""跨会话长期记忆工具。"""

from __future__ import annotations

import typing

import agent.tools._memory_store

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
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
}


class MemoryTool:
    """Agent 长期记忆的增删改查。"""

    def __init__(self, agent_name: str) -> None:
        self.__agent_name = agent_name

    def add_item(self, key: str, value: str) -> str:
        """添加记忆条目。"""
        normalized_key, key_error = agent.tools._memory_store.validate_key(key)
        if key_error is not None:
            return key_error
        normalized_value, value_error = agent.tools._memory_store.validate_value(value)
        if value_error is not None:
            return value_error

        items = agent.tools._memory_store.load_items(self.__agent_name)
        if agent.tools._memory_store.find_key(items, normalized_key) is not None:
            return f"错误：已存在标题为「{normalized_key}」的记忆，请改用 update_item。"
        items[normalized_key] = agent.tools._memory_store.create_memory_item(normalized_value)
        save_error = agent.tools._memory_store.save_items(items, self.__agent_name)
        if save_error is not None:
            return save_error
        return f"已添加记忆「{normalized_key}」。"

    def remove_item(self, key: str) -> str:
        """删除记忆条目。"""
        normalized_key, key_error = agent.tools._memory_store.validate_key(key)
        if key_error is not None:
            return key_error

        items = agent.tools._memory_store.load_items(self.__agent_name)
        existing = agent.tools._memory_store.find_key(items, normalized_key)
        if existing is None:
            return f"错误：未找到标题为「{normalized_key}」的记忆。"
        del items[existing]
        save_error = agent.tools._memory_store.save_items(items, self.__agent_name)
        if save_error is not None:
            return save_error
        return f"已删除记忆「{existing}」。"

    def update_item(self, key: str, value: str) -> str:
        """更新记忆条目。"""
        normalized_key, key_error = agent.tools._memory_store.validate_key(key)
        if key_error is not None:
            return key_error
        normalized_value, value_error = agent.tools._memory_store.validate_value(value)
        if value_error is not None:
            return value_error

        items = agent.tools._memory_store.load_items(self.__agent_name)
        existing = agent.tools._memory_store.find_key(items, normalized_key)
        if existing is None:
            return f"错误：未找到标题为「{normalized_key}」的记忆，请改用 add_item。"
        items[existing] = agent.tools._memory_store.create_memory_item(normalized_value)
        save_error = agent.tools._memory_store.save_items(items, self.__agent_name)
        if save_error is not None:
            return save_error
        return f"已更新记忆「{existing}」。"

    def list_items(self, filter: str | None = None) -> str:  # pylint: disable=redefined-builtin
        """列出记忆条目，可按标题正则筛选。"""
        items = agent.tools._memory_store.load_items(self.__agent_name)
        filter_text = filter.strip() if filter else ""
        matches = agent.tools._memory_store.sort_items_by_updated_at(items)
        if filter_text:
            regex, regex_error = agent.tools._memory_store.compile_ignore_case_regex(filter_text)
            if regex_error is not None:
                return regex_error
            matches = [pair for pair in matches if regex.search(pair[0])]

        lines = [agent.tools._memory_store.RELIABILITY_NOTICE]
        if not matches:
            if filter_text:
                lines.append(f"(无匹配「{filter_text}」的记忆)")
            else:
                lines.append("(无记忆)")
            return "\n".join(lines)

        for title, item in matches:
            updated = agent.tools._memory_store.format_updated_at(item["updated_at"])
            lines.append(f"## {title} · {updated}")
        return "\n".join(lines)

    def find_str(self, pattern: str) -> str:
        """在记忆标题与正文中搜索。"""
        filter_text = pattern.strip()
        if not filter_text:
            return "错误：pattern 不能为空。"
        regex, regex_error = agent.tools._memory_store.compile_ignore_case_regex(filter_text)
        if regex_error is not None:
            return regex_error

        items = agent.tools._memory_store.load_items(self.__agent_name)
        matches = [
            pair
            for pair in agent.tools._memory_store.sort_items_by_updated_at(items)
            if regex.search(pair[0]) or regex.search(pair[1]["value"])
        ]
        lines = [agent.tools._memory_store.RELIABILITY_NOTICE]
        if not matches:
            lines.append(f"(未找到匹配「{filter_text}」的记忆)")
            return "\n".join(lines)

        for title, item in matches:
            updated = agent.tools._memory_store.format_updated_at(item["updated_at"])
            lines.append(f"## {title} · {updated}")
            lines.append(item["value"])
            lines.append("")
        return "\n".join(lines).rstrip()
