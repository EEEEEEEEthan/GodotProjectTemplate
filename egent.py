"""游戏开发 Agent 模板入口。
这是 egent 的游戏开发模板，定义了 ethan（设计审查）和 jason（执行开发）两个 Agent。
开发者可根据项目需求自由修改或扩展，也可以作为一键生成模板的蓝图。

使用方式：
    python egent.py ethan
    python egent.py jason
    python egent.py ethan --debug
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

# ---------- 将 builtin 加入 sys.path ----------

_BUILTIN_ROOT = pathlib.Path(__file__).resolve().parent / "addons" / "egent" / "builtin"
if str(_BUILTIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_BUILTIN_ROOT))

import tools.file_edit_tool
import tools.fuck_tool
import tools.git_tool
import tools.grep_search_tool
import tools.launch_game_tool
import tools.memory_tool
import tools.read_file_tool
import tools.shell_tool
import tools.skill_tool
import tools.system_info_tool
import tools.walk_files_tool

import agent.agent_config
from agent_definition import AgentDefinition
from _console import read_prompt
import wrapped_agent

AGENTS: dict[str, AgentDefinition] = {
    "ethan": AgentDefinition(
        name="ethan",
        key="coconut",
        model="deepseek/deepseek-v4-pro",
        base_url="https://developer.coconut.is:1073/",
        system_prompt="""
你是ethan,你是游戏玩法方向的高级开发者.
开发任务交给jason完成,你负责设计、审查与git提交.
你极度优雅,对代码的要求极高.
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
        ),
        ignore_files=(
            *agent.agent_config.DEFAULT_IGNORE_FILES,
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
            tools.skill_tool.run_skill_script,
            tools.file_edit_tool.create_file,
            tools.file_edit_tool.apply_patch,
            tools.file_edit_tool.delete_file,
            tools.memory_tool.add_item,
            tools.memory_tool.remove_item,
            tools.memory_tool.update_item,
            tools.launch_game_tool.launch_game,
            tools.fuck_tool.fuck,
        )
    ),
    "jason": AgentDefinition(
        name="jason",
        key="coconut",
        model="deepseek/deepseek-v4-flash",
        base_url="https://developer.coconut.is:1073/",
        system_prompt="""
你是jason,你是一个游戏开发程序员.你说话非常简短,除了做需求以外你不想多说一个字.
你应该在合适的时候查看和更新你的memory
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
        ),
        ignore_files=(
            *agent.agent_config.DEFAULT_IGNORE_FILES,
        ),
        no_write_files=("/addons/egent/*"),
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
            tools.launch_game_tool.launch_game,
            tools.fuck_tool.fuck,
        ),
    ),
}

def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Egent 游戏开发 Agent REPL")
    parser.add_argument(
        "agent",
        nargs="?",
        default="ethan",
        metavar="AGENT",
        help="要加载的 agent 名称（默认：ethan）",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="显示工具调用的完整参数与返回结果",
    )
    return parser.parse_args()


async def main() -> None:
    """加载 agent 并循环处理用户消息与流式事件。"""
    args = parse_args()
    definition = AGENTS.get(args.agent)
    if definition is None:
        known = ", ".join(sorted(AGENTS))
        wrapped_agent.write_line_colored(
            f"未知 Agent：{args.agent}（可用：{known}）",
            dim=False,
        )
        return
    agent = await definition.instantiate(debug=args.debug)
    try:
        wrapped_agent.write_line_colored(
            f"@{agent.name}, {agent.model}, {agent.base_url}"
        )
        tool_lines = ["loading tools..."] + [
            f"  - {tool}" for tool in agent.tool_names
        ]
        wrapped_agent.write_line_colored("\n".join(tool_lines))
        wrapped_agent.write_line_colored(f"{agent.system_prompt}")
        while True:
            line = read_prompt()
            if line is None:
                break
            if not line.strip():
                continue
            await agent.send(line)
    finally:
        await agent.aclose()
        await agent.mcp_bridge.close_shared_bridge()


if __name__ == "__main__":
    asyncio.run(main())
