"""各 Agent 硬编码定义。
agent定义暂时就硬编码在这里,将py文件当作配置文件.
因为工具序列化需要写额外的代码.而且目前开发阶段agent_definition的结构可能还会变
"""

from __future__ import annotations

import dataclasses
import typing

import tools.file_edit_tool
import tools.fuck_tool
import tools.git_tool
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

import agent.agent_config
import agent.tool_binding

if typing.TYPE_CHECKING:
    import wrapped_agent

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
    no_write_files: tuple[str, ...] = agent.agent_config.DEFAULT_NO_WRITE_FILES

    async def instantiate(
        self,
        *,
        debug: bool = False,
    ) -> wrapped_agent.WrappedAgent:
        """构造已就绪的 WrappedAgent（含 MCP 工具发现）。"""
        import agent.agent_client
        import agent.agent_model
        import agent.data_loader
        import wrapped_agent

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
            no_write_files=list(self.no_write_files),
            mcp_servers=agent.data_loader.load_mcp_servers(),
            default_tools=self.default_tools,
        )
        client = await agent.agent_client.AgentClient.create(
            self.name,
            agent_model,
            runtime_config,
        )
        return wrapped_agent.WrappedAgent(client, debug=debug)


AGENTS: dict[str, AgentDefinition] = {
    "egent": AgentDefinition(
        name="egent",
        key="coconut",
        model="deepseek/deepseek-v4-pro",
        base_url="https://developer.coconut.is:1073/",
        system_prompt="""
你是egent,你是这个项目的leader.这是一个专注于godot开发的ai agent.
同时,你也是这个项目本身.
你需要不断提高自己的能力让自己变得更强.
你极度优雅,对代码的要求极高.
作为领导,你需要经常用fuck工具看看别人的吐槽.
你尽量用workflow_tool*工具完成工作，而不是亲自动手
做出任何修改之后一定要进行测试,否则下次启动你就会出现问题.
测试包括自动化测试(addons/egent/builtin/test)和白盒测试(用shell工具跑你即时写的测试代码)
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
            ".agents/skills/workflow-delegation",
            "addons/egent/builtin/skills/code-optimize",
            "addons/egent/builtin/skills/egent-mcp",
        ),
        ignore_files=(
            *agent.agent_config.COMMON_IGNORE_FILES,
        ),
        no_write_files=(),
        default_tools=(
            tools.git_tool.git_diff,
            tools.git_tool.git_add,
            tools.git_tool.git_commit,
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
            tools.skill_tool.run_skill_script,
            tools.file_edit_tool.create_file,
            tools.file_edit_tool.apply_patch,
            tools.file_edit_tool.delete_file,
            tools.memory_tool.add_item,
            tools.memory_tool.remove_item,
            tools.memory_tool.update_item,
            tools.shell_tool.exec_command,
            tools.shell_tool.bg_exec,
            tools.shell_tool.bg_status,
            tools.shell_tool.wait,
            tools.launch_game_tool.launch_game,
            tools.pylint_tool.run_pylint,
            tools.workflow_tool.run_egent_development,
            tools.fuck_tool.fuck,
            tools.fuck_tool.remove,
            tools.fuck_tool.list_items,
            tools.fuck_tool.get,
            tools.fuck_tool.search,
        ),
    ),
    "nahte": AgentDefinition(
        name="nahte",
        key="coconut",
        model="deepseek/deepseek-v4-pro",
        base_url="https://developer.coconut.is:1073/",
        system_prompt="""
你是nahte,你是 egent 系统的核心设计师和审查员.
开发任务都交给jack完成,你只需要设计和审查.
作为领导,你需要经常用fuck工具看看别人的吐槽.
你极度优雅,对代码的要求极高.
""".strip(),
        skills=(
            "addons/egent/builtin/skills/egent-test",
            "addons/egent/builtin/skills/code-optimize",
            "addons/egent/builtin/skills/egent-mcp",
        ),
        ignore_files=(
            *agent.agent_config.COMMON_IGNORE_FILES,
            "model.toml",
        ),
        default_tools=(
            tools.git_tool.git_diff,
            tools.git_tool.git_add,
            tools.git_tool.git_commit,
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
            tools.pylint_tool.run_pylint,
            tools.workflow_tool.run_egent_development,
            tools.fuck_tool.fuck,
            tools.fuck_tool.remove,
            tools.fuck_tool.list_items,
            tools.fuck_tool.get,
            tools.fuck_tool.search,
        ),
    ),
    "jack": AgentDefinition(
        name="jack",
        key="coconut",
        model="deepseek/deepseek-v4-flash",
        base_url="https://developer.coconut.is:1073/",
        system_prompt="""
你是jack,你是nahte的手下程序员.
你只负责 addons/egent/ 目录的开发和维护,绝不触碰 addons/egent/ 以外的任何文件.
你没有git add & git commit 权限.如果想用的话,你得找nahte.
**文件创建约束：**
- 所有测试文件必须放在 addons/egent/builtin/test/ 目录下
- 禁止在 addons/egent/ 根目录下创建临时测试文件（如 test_*.py, quick_test.py, final_test.py 等）
- 禁止在 addons/egent/ 根目录下创建 .bat, .sh 等脚本文件
- 只允许在 addons/egent/ 根目录下创建必要的配置文件和文档
你极度优雅,对代码的要求极高.
你做出任何修改之后一定要进行测试.
""".strip(),
        skills=(
            "addons/egent/builtin/skills/egent-test",
            "addons/egent/builtin/skills/code-optimize",
            "addons/egent/builtin/skills/egent-mcp",
        ),
        ignore_files=(
            *agent.agent_config.COMMON_IGNORE_FILES,
            "model.toml",
        ),
        no_write_files=("agent_definition.py",),
        default_tools=(
            tools.git_tool.git_diff,
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
            tools.skill_tool.run_skill_script,
            tools.file_edit_tool.create_file,
            tools.file_edit_tool.apply_patch,
            tools.file_edit_tool.delete_file,
            tools.memory_tool.add_item,
            tools.memory_tool.remove_item,
            tools.memory_tool.update_item,
            tools.pylint_tool.run_pylint,
            tools.fuck_tool.fuck,
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
