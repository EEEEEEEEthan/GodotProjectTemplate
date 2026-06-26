"""Agent 默认配置：系统提示词与内置 skill 路径。"""

import dataclasses
import typing

import agent.agent_tools


DEFAULT_SYSTEM_PROMPT = "你是我的助手。你应该在合适的时候查看和更新你的memory"

DEFAULT_SKILLS = [
    ".ethan/builtin-skills/auto-test",
    ".ethan/builtin-skills/create-file",
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
    ".ethan",
    ".venv",
    ".temp",
)


@dataclasses.dataclass
class AgentConfig:
    """Agent 运行时配置：skills、工具白名单与系统提示词。"""

    skills: list[str] = dataclasses.field(default_factory=lambda: list(DEFAULT_SKILLS))
    tool_whitelist: list[str] = dataclasses.field(
        default_factory=lambda: list(agent.agent_tools.TOOL_SCHEMAS)
    )
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ignore_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_IGNORE_FILES)
    )
    mcp_servers: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
