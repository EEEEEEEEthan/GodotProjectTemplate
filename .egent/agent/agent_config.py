"""Agent 默认配置：系统提示词、内置 skill 路径与默认工具集。"""

from __future__ import annotations

import dataclasses
import typing

import agent.tool_binding
import agent.builtin_tools.file_edit_tool as file_edit_tool
import agent.builtin_tools.fuck_tool as fuck_tool
import agent.builtin_tools.grep_search_tool as grep_search_tool
import agent.builtin_tools.launch_game_tool as launch_game_tool
import agent.builtin_tools.memory_tool as memory_tool
import agent.builtin_tools.read_file_tool as read_file_tool
import agent.builtin_tools.shell_tool as shell_tool
import agent.builtin_tools.skill_tool as skill_tool
import agent.builtin_tools.system_info_tool as system_info_tool
import agent.builtin_tools.walk_files_tool as walk_files_tool


DEFAULT_SYSTEM_PROMPT = "你是我的助手。你应该在合适的时候查看和更新你的memory"

DEFAULT_SKILLS = [
    ".egent/builtin-skills/auto-test",
    ".egent/builtin-skills/create-file",
]

DEFAULT_IGNORE_FILES: tuple[str, ...] = (
    ".git",
    ".idea",
    ".vs",
    "__pycache__",
    "node_modules",
    "bin",
    "obj",
    "*.pyc",
    ".agents",
    ".cursor",
    ".claude",
    ".egent",
    ".venv",
    ".temp",
)

BASIC_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    skill_tool.learn_skill,
    grep_search_tool.grep_search,
    walk_files_tool.walk_files,
    system_info_tool.system_info,
    memory_tool.list_items,
    memory_tool.find_str,
    read_file_tool.read_file_outline_cs,
    read_file_tool.read_file_outline_md,
    read_file_tool.read_file_outline_py,
    read_file_tool.read_lines,
    read_file_tool.read_whole_file,
)

DEV_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    skill_tool.run_skill_script,
    file_edit_tool.create_file,
    file_edit_tool.apply_patch,
    memory_tool.add_item,
    memory_tool.remove_item,
    memory_tool.update_item,
    fuck_tool.fuck,
)

ADMIN_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    shell_tool.exec,
    shell_tool.bg_exec,
    shell_tool.bg_status,
    shell_tool.wait,
)

GAME_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    launch_game_tool.launch_game,
)

ALL_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    *BASIC_TOOLS,
    *DEV_TOOLS,
    *ADMIN_TOOLS,
    *GAME_TOOLS,
)

DEFAULT_TOOLS = ALL_TOOLS


@dataclasses.dataclass
class AgentConfig:
    """Agent 运行时配置：skills、系统提示词、工具集与 MCP。"""

    skills: list[str] = dataclasses.field(default_factory=lambda: list(DEFAULT_SKILLS))
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ignore_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_IGNORE_FILES)
    )
    mcp_servers: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    default_tools: tuple[agent.tool_binding.ToolHandler, ...] = ALL_TOOLS
