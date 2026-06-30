"""Agent 默认配置：系统提示词、内置 skill 路径与默认工具集。"""

from __future__ import annotations

import dataclasses
import typing

import agent.tool_binding


DEFAULT_SYSTEM_PROMPT = "你是我的助手。你应该在合适的时候查看和更新你的memory"

COMMON_IGNORE_FILES: tuple[str, ...] = (
    ".git",
    ".idea",
    ".vs",
    "__pycache__",
    "node_modules",
    "*.pyc",
    ".agents",
    ".cursor",
    ".claude",
    ".venv",
    ".temp",
)

EGENT_IGNORE_FILES: tuple[str, ...] = (".egent",)

DEFAULT_IGNORE_FILES: tuple[str, ...] = (*COMMON_IGNORE_FILES, *EGENT_IGNORE_FILES)

DEFAULT_NO_WRITE_FILES: tuple[str, ...] = (
    ".egent",
    "*.pyc",
)


@dataclasses.dataclass
class AgentConfig:
    """Agent 运行时配置：skills、系统提示词、工具集与 MCP。"""

    skills: list[str] = dataclasses.field(default_factory=lambda: [])
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ignore_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_IGNORE_FILES)
    )
    no_write_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_NO_WRITE_FILES)
    )
    mcp_servers: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    default_tools: tuple[agent.tool_binding.ToolHandler, ...] = ()
