"""Egent 交互式 REPL 入口。"""

import argparse
import asyncio
import pathlib
import sys

_BUILTIN_ROOT = pathlib.Path(__file__).resolve().parent
if str(_BUILTIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_BUILTIN_ROOT))

import agent_definition
import agent.mcp_bridge
import wrapped_agent
from _console import read_prompt


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="Egent 交互式 REPL")
    parser.add_argument(
        "agent",
        nargs="?",
        default="jason",
        metavar="AGENT",
        help="要加载的 agent 名称（默认：jason）",
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
    definition = agent_definition.AGENTS.get(args.agent)
    if definition is None:
        known = ", ".join(sorted(agent_definition.AGENTS))
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
