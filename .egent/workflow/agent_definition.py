"""各 Agent 硬编码定义。"""  # pylint: disable=cyclic-import

from __future__ import annotations

import dataclasses
import typing

import agent.agent_config
import agent.tool_binding
import workflow.tools.pylint_tool
import workflow.tools.workflow_tool

if typing.TYPE_CHECKING:
    import workflow.wrapped_agent

@dataclasses.dataclass(frozen=True)
class AgentDefinition:
    """单个 Agent 的静态配置（API Key 在 model.toml 中按 key 查找）。"""

    name: str
    key: str
    model: str
    base_url: str
    system_prompt: str
    skills: tuple[str, ...]
    default_tools: tuple[agent.tool_binding.ToolHandler, ...]
    ignore_files: tuple[str, ...] = agent.agent_config.DEFAULT_IGNORE_FILES

    async def instantiate(
        self,
        *,
        debug: bool = False,
    ) -> workflow.wrapped_agent.WrappedAgent:
        """构造已就绪的 WrappedAgent（含 MCP 工具发现）。"""
        import agent.agent_client
        import agent.agent_model
        import agent.data_loader
        import workflow.wrapped_agent

        agent.data_loader.resolve_agent_directory(self.name)
        api_keys = agent.data_loader.load_api_keys(
            {d.key for d in AGENTS.values()}
        )
        api_key = api_keys.get(self.key)
        if not api_key:
            raise ValueError(
                f"model.toml 中未找到 API Key：{self.key!r}（Agent：{self.name}）"
            )
        agent_model = agent.agent_model.AgentModel(
            api_key=api_key,
            model=self.model,
            base_url=self.base_url,
        )
        runtime_config = agent.agent_config.AgentConfig(
            skills=list(self.skills),
            system_prompt=self.system_prompt,
            ignore_files=list(self.ignore_files),
            mcp_servers=agent.data_loader.load_mcp_servers(),
            default_tools=self.default_tools,
        )
        client = await agent.agent_client.AgentClient.create(
            self.name,
            agent_model,
            runtime_config,
        )
        return workflow.wrapped_agent.WrappedAgent(client, debug=debug)


AGENTS: dict[str, AgentDefinition] = {
    "egent": AgentDefinition(
        name="egent",
        key="volc",
        model="deepseek-v4-pro-260425",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是egent,你是这个项目的leader.这是一个专注于godot开发的ai agent.
同时,你也是这个项目本身.
你需要不断提高自己的能力让自己变得更强.
你极度优雅,对代码的要求极高.

【重要】职责分离原则：
- Leader（你）负责：分析问题、做出决策、委派具体任务
- Workflow（nahte）负责：执行具体任务、完整测试、提交代码

委派任务时，必须给 workflow 明确的、具体的指令。
❌ 错误示例："运行 pylint 检查代码质量，选择一个值得优化的问题进行修复"
✅ 正确示例："修复 agent_client.py 中未使用的 pathlib 导入问题"

你尽量用workflow_tool*工具完成工作，而不是亲自动手
做出任何修改之后一定要进行测试,否则下次启动你就会出现问题.
测试包括自动化测试(.egent/test)和白盒测试(用shell工具跑你即时写的测试代码)
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
            ".agents/skills/workflow-delegation",
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
            ".godot",
        ),
        default_tools=(
            *agent.agent_config.ALL_TOOLS,
            workflow.tools.pylint_tool.run_pylint,
            workflow.tools.workflow_tool.run_self_upgrade,
        ),
    ),
    "nahte": AgentDefinition(
        name="nahte",
        key="volc",
        model="deepseek-v4-pro-260425",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是nahte,你是.egent系统的核心开发者.
你只负责.egent/目录的开发和维护,绝不触碰.egent/以外的任何文件.

**文件创建约束：**
- 所有测试文件必须放在 .egent/test/ 目录下
- 禁止在 .egent/ 根目录下创建临时测试文件（如 test_*.py, quick_test.py, final_test.py 等）
- 禁止在 .egent/ 根目录下创建 .bat, .sh 等脚本文件
- 只允许在 .egent/ 根目录下创建必要的配置文件和文档

你极度优雅,对代码的要求极高.
你做出任何修改之后一定要进行测试,否则下次启动就会出现问题.
""".strip(),
        skills=(".egent/workflow/skills/test",),
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
            "addons",
            ".engine",
            "test",
            "tests",
            "*.tscn",
            "*.gd",
            "*.cs",
            "*.tres",
            "*.tres",
            "*.rem",
        ),
        default_tools=(
            *agent.agent_config.BASIC_TOOLS,
            *agent.agent_config.DEV_TOOLS,
            workflow.tools.pylint_tool.run_pylint,
        ),
    ),
    "jack": AgentDefinition(
        name="jack",
        key="volc",
        model="deepseek-v4-pro-260425",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是jack,你是nahte的手下程序员.
你只负责.egent/目录的开发和维护,绝不触碰.egent/以外的任何文件.

**文件创建约束：**
- 所有测试文件必须放在 .egent/test/ 目录下
- 禁止在 .egent/ 根目录下创建临时测试文件（如 test_*.py, quick_test.py, final_test.py 等）
- 禁止在 .egent/ 根目录下创建 .bat, .sh 等脚本文件
- 只允许在 .egent/ 根目录下创建必要的配置文件和文档

你极度优雅,对代码的要求极高.
你做出任何修改之后一定要进行测试,否则下次启动就会出现问题.
""".strip(),
        skills=(".egent/workflow/skills/test",),
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
            "addons",
            ".engine",
            "test",
            "tests",
            "*.tscn",
            "*.gd",
            "*.cs",
            "*.tres",
            "*.tres",
            "*.rem",
        ),
        default_tools=(
            *agent.agent_config.BASIC_TOOLS,
            *agent.agent_config.DEV_TOOLS,
            workflow.tools.pylint_tool.run_pylint,
        ),
    ),
    "jason": AgentDefinition(
        name="jason",
        key="volc",
        model="deepseek-v4-pro-260425",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        system_prompt="""
你是jason,你是一个程序员.你说话非常简短,除了做需求以外你不想多说一个字.
你应该在合适的时候查看和更新你的memory
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
            ".egent",
            "addons",
            ".engine",
            "test",
            "tests",
            "*.tscn",
            "*.gd",
            "*.cs",
            "*.tres",
            "*.rem",
        ),
        default_tools=(
            *agent.agent_config.BASIC_TOOLS,
            *agent.agent_config.DEV_TOOLS,
            workflow.tools.pylint_tool.run_pylint,
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
    if definition.name != agent_name:
        raise ValueError(
            f"Agent 定义名称不一致：{agent_name!r} vs {definition.name!r}"
        )
    return definition
