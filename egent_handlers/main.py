"""游戏开发 Agent 模板入口。
这是 egent 的游戏开发模板，定义了 ethan（设计审查）和 jason（执行开发）两个 Agent。
开发者可根据项目需求自由修改或扩展，也可以作为一键生成模板的蓝图。

使用方式：
    egent.bat ethan
    egent.bat jason
    egent.bat ethan --debug
    egent.bat --test egent_handlers/tests/hello_test.gd
    egent.bat --test egent_handlers/tests/hello_test.gd --headless
    egent.bat --test-folder egent_handlers/tests
    egent.bat --test-folder egent_handlers/tests --headless
"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys
import typing

_PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
_EGENT_ROOT = _PROJECT_ROOT / "addons" / "egent"
_BUILTIN_ROOT = _EGENT_ROOT / "builtin"
if str(_BUILTIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_BUILTIN_ROOT))
if str(_EGENT_ROOT) not in sys.path:
    sys.path.append(str(_EGENT_ROOT))

from builtin import tools, wrapped_agent
from builtin.agent import agent_config, mcp_bridge
from builtin.agent_definition import AgentDefinition
from builtin._console import read_prompt
from godot_test import run_file, run_folder

TESTS_FOLDER = "egent_handlers/tests"
# pylint: enable=wrong-import-position

async def _run_game_development(agent_client: typing.Any, prompt: str) -> str:
    """执行游戏开发工作流：委派任务给 jason

    @param prompt: 任务描述.需要包括任务原因,任务细节,关键代码位置
    """
    del agent_client
    task_prompt = prompt.strip()
    if not task_prompt:
        return "错误：prompt 不能为空。"

    jason = None
    try:
        jason = await AGENTS["jason"].instantiate()
        await jason.send(task_prompt)

        for attempt in range(10):
            tests_passed, tests_info = await asyncio.to_thread(
                run_folder, TESTS_FOLDER, headless=True
            )
            if tests_passed:
                break
            await jason.send(
                f"你的需求是:{task_prompt}\n，很遗憾测试未通过（第{attempt+1}次）：\n{tests_info}\n请修复"
            )
        else:
            lst_report = await jason.send(
                "测试未通过，我们决定取消本次工作。写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                override_tools=(),
            )
            return "\n".join(lst_report)

        lst_report = await jason.send(
            "写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
            override_tools=(),
        )
        return "\n".join(lst_report) + "\n\n任务完成。请审查 git diff 后决定是否提交。"
    except Exception as error:  # pylint: disable=broad-exception-caught
        return f"错误：游戏开发工作流执行失败：{error}"
    finally:
        if jason is not None:
            await jason.aclose()


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

【重要】职责分离原则：
- Leader（你）负责：分析问题、做出决策、委派具体任务
- Workflow（jason）负责：执行具体任务、完整测试

委派任务时，必须给 workflow 明确的、具体的指令。
❌ 错误示例："运行 pylint 检查代码质量，选择一个值得优化的问题进行修复"
✅ 正确示例："修复 agent_client.py 中未使用的 pathlib 导入问题"

你尽量用 _run_game_development 工具完成工作，而不是亲自动手
做出任何修改之后一定要进行测试,否则下次启动你就会出现问题.
""".strip(),
        skills=(
            ".agents/skills/godot-autotest",
            ".agents/skills/godot-mcp-eval",
        ),
        ignore_files=(
            *agent_config.DEFAULT_IGNORE_FILES,
        ),
        default_tools=(
            tools.file_edit_tool.apply_patch,
            tools.file_edit_tool.create_file,
            tools.file_edit_tool.delete_file,
            tools.fuck_tool.fuck,
            tools.git_tool.git_add,
            tools.git_tool.git_commit,
            tools.git_tool.git_diff,
            tools.godot_test_tool.run_godot_test,
            tools.grep_search_tool.grep_search,
            tools.launch_game_tool.launch_game,
            tools.memory_tool.add_item,
            tools.memory_tool.find_str,
            tools.memory_tool.list_items,
            tools.memory_tool.remove_item,
            tools.memory_tool.update_item,
            tools.read_file_tool.read_file_outline_cs,
            tools.read_file_tool.read_file_outline_md,
            tools.read_file_tool.read_file_outline_py,
            tools.read_file_tool.read_lines,
            tools.read_file_tool.read_whole_file,
            tools.skill_tool.learn_skill,
            tools.skill_tool.run_skill_script,
            tools.system_info_tool.system_info,
            tools.walk_files_tool.walk_files,
            _run_game_development,
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
            *agent_config.DEFAULT_IGNORE_FILES,
        ),
        no_write_files=("/addons/egent/*",),
        default_tools=(
            tools.file_edit_tool.apply_patch,
            tools.file_edit_tool.create_file,
            tools.file_edit_tool.delete_file,
            tools.fuck_tool.fuck,
            tools.git_tool.git_diff,
            tools.godot_test_tool.run_godot_test,
            tools.grep_search_tool.grep_search,
            tools.launch_game_tool.launch_game,
            tools.memory_tool.add_item,
            tools.memory_tool.find_str,
            tools.memory_tool.list_items,
            tools.memory_tool.remove_item,
            tools.memory_tool.update_item,
            tools.read_file_tool.read_file_outline_cs,
            tools.read_file_tool.read_file_outline_md,
            tools.read_file_tool.read_file_outline_py,
            tools.read_file_tool.read_lines,
            tools.read_file_tool.read_whole_file,
            tools.skill_tool.learn_skill,
            tools.skill_tool.run_skill_script,
            tools.system_info_tool.system_info,
            tools.walk_files_tool.walk_files,
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Egent 游戏开发 Agent REPL")
    parser.add_argument(
        "agent",
        nargs="?",
        default=None,
        metavar="AGENT",
        help="要加载的 agent 名称（默认：ethan）",
    )
    parser.add_argument(
        "--test",
        metavar="SCRIPT",
        help="运行 Godot 自动化测试（GD 脚本路径）",
    )
    parser.add_argument(
        "--test-folder",
        metavar="FOLDER",
        help="并发运行文件夹下全部 .gd 测试",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行 Godot 测试",
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
    if args.test is not None:
        message = await asyncio.to_thread(
            run_file, args.test, headless=args.headless
        )
        print(message)
        sys.exit(0 if message.startswith("[PASS]") else 1)

    if args.test_folder is not None:
        tests_passed, message = await asyncio.to_thread(
            run_folder, args.test_folder, headless=args.headless
        )
        print(message)
        sys.exit(0 if tests_passed else 1)

    agent_name = args.agent or "ethan"
    definition = AGENTS.get(agent_name)
    if definition is None:
        known = ", ".join(sorted(AGENTS))
        wrapped_agent.write_line_colored(
            f"未知 Agent：{agent_name}（可用：{known}）",
            dim=False,
        )
        return
    repl_agent = await definition.instantiate(debug=args.debug)
    try:
        wrapped_agent.write_line_colored(
            f"@{repl_agent.name}, {repl_agent.model}, {repl_agent.base_url}"
        )
        tool_lines = ["loading tools..."] + [
            f"  - {tool}" for tool in repl_agent.tool_names
        ]
        wrapped_agent.write_line_colored("\n".join(tool_lines))
        wrapped_agent.write_line_colored(f"{repl_agent.system_prompt}")
        while True:
            line = read_prompt()
            if line is None:
                break
            if not line.strip():
                continue
            await repl_agent.send(line)
    finally:
        await repl_agent.aclose()
        await mcp_bridge.close_shared_bridge()


if __name__ == "__main__":
    asyncio.run(main())
