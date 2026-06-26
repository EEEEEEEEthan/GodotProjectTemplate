"""各 Agent 硬编码配置。"""

from __future__ import annotations

import dataclasses

_DEFAULT_IGNORE_FILES: tuple[str, ...] = (
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


@dataclasses.dataclass(frozen=True)
class AgentDefinition:
    """单个 Agent 的静态配置（API Key 在 model.toml 中按 key 查找）。"""

    key: str
    model: str
    base_url: str
    system_prompt: str
    skills: tuple[str, ...]
    ignore_files: tuple[str, ...] = _DEFAULT_IGNORE_FILES


AGENTS: dict[str, AgentDefinition] = {
    "jason": AgentDefinition(
        key="volc",
        model="glm-4-7-251222",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是jason,你是一个程序员.你说话非常简短,除了做需求以外你不想多说一个字.
你应该在合适的时候查看和更新你的memory
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
        ),
    ),
    "egent": AgentDefinition(
        key="volc",
        model="glm-4-7-251222",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是egent,你是这个项目的leader.这是一个专注于godot开发的ai agent.
同时,你也是这个项目本身.
你需要不断提高自己的能力让自己变得更强.
你极度优雅,对代码的要求极高.
你做出任何修改之后一定要进行测试,否则下次启动你就会出现问题.
测试包括自动化测试(.egent/test)和白盒测试(用shell工具跑你即时写的测试代码)
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
        ),
        ignore_files=(
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
            ".venv",
            ".temp",
        ),
    ),
}


def get_definition(name: str) -> AgentDefinition:
    """按名称获取 Agent 定义。"""
    agent_name = name.strip()
    if not agent_name:
        raise ValueError("agent_name 不能为空")
    definition = AGENTS.get(agent_name)
    if definition is None:
        known = ", ".join(sorted(AGENTS))
        raise KeyError(f"未知 Agent：{agent_name}（可用：{known}）")
    return definition
