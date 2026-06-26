"""Agent 默认配置：系统提示词与内置 skill 路径。"""

import dataclasses
import typing


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


@dataclasses.dataclass
class AgentConfig:
    """Agent 运行时配置：skills、系统提示词与 MCP。"""

    skills: list[str] = dataclasses.field(default_factory=lambda: list(DEFAULT_SKILLS))
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    ignore_files: list[str] = dataclasses.field(
        default_factory=lambda: list(DEFAULT_IGNORE_FILES)
    )
    mcp_servers: dict[str, typing.Any] = dataclasses.field(default_factory=dict)
