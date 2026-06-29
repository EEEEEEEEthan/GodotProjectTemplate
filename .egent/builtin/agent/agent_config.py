"""Agent 默认配置：系统提示词、内置 skill 路径与默认工具集。"""

from __future__ import annotations

import dataclasses
import typing

import agent.tool_binding
import tools.file_edit_tool
import tools.fuck_tool
import tools.grep_search_tool
import tools.launch_game_tool
import tools.memory_tool
import tools.pylint_tool
import tools.read_file_tool
import tools.shell_tool
import tools.skill_tool
import tools.system_info_tool
import tools.walk_files_tool
import tools.workflow_tool


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
    tools.skill_tool.learn_skill,
    tools.grep_search_tool.grep_search,
    tools.walk_files_tool.walk_files,
    tools.system_info_tool.system_info,
    tools.memory_tool.list_items,
    tools.memory_tool.find_str,
    tools.read_file_tool.read_file_outline_cs,
    tools.read_file_tool.read_file_outline_md,
    tools.read_file_tool.read_file_outline_py,
    tools.read_file_tool.read_lines,
    tools.read_file_tool.read_whole_file,
)

DEV_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    tools.skill_tool.run_skill_script,
    tools.file_edit_tool.create_file,
    tools.file_edit_tool.apply_patch,
    tools.file_edit_tool.delete_file,
    tools.memory_tool.add_item,
    tools.memory_tool.remove_item,
    tools.memory_tool.update_item,
    tools.fuck_tool.fuck,
)

ADMIN_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    tools.shell_tool.exec_command,
    tools.shell_tool.bg_exec,
    tools.shell_tool.bg_status,
    tools.shell_tool.wait,
)

GAME_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    tools.launch_game_tool.launch_game,
)

EGENT_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    tools.pylint_tool.run_pylint,
)

EGENT_WORKFLOW_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    tools.workflow_tool.run_self_upgrade,
)

DEFAULT_TOOLS: tuple[agent.tool_binding.ToolHandler, ...] = (
    *BASIC_TOOLS,
    *DEV_TOOLS,
    *GAME_TOOLS,
)


@dataclasses.dataclass
class AgentConfig:
    """Agent 运行时配置：skills、系统提示词、工具集与 MCP。"""

    skills: list[str] = dataclasses.field(default_factory=lambda: list(DEFAULT_SKILLS))
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ignore_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_IGNORE_FILES)
    )
    mcp_servers: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    default_tools: tuple[agent.tool_binding.ToolHandler, ...] = DEFAULT_TOOLS
