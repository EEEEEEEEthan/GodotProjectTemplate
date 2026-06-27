"""Egent 交互式 REPL 入口。"""

import argparse
import asyncio
import pathlib
import sys

_EGENT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_EGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EGENT_ROOT))

import loop.agent_config
import loop.wrapped_agent


def read_prompt() -> str | None:
    """读取一行用户输入，EOF 时返回 None。"""
    sys.stdout.write("> ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n")


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
    definition = loop.agent_config.AGENTS.get(args.agent)
    if definition is None:
        known = ", ".join(sorted(loop.agent_config.AGENTS))
        loop.wrapped_agent.write_line_colored(
            f"未知 Agent：{args.agent}（可用：{known}）",
            dim=False,
        )
        return
    agent = await definition.instantiate(debug=args.debug)
    try:
        client = agent.client
        loop.wrapped_agent.write_line_colored(
            f"@{client.name}, {client.model}, {client.base_url}"
        )
        tool_lines = ["loading tools..."] + [
            f"  - {tool}" for tool in client.tool_names
        ]
        loop.wrapped_agent.write_line_colored("\n".join(tool_lines))
        loop.wrapped_agent.write_line_colored(f"{client.system_prompt}")
        while True:
            line = read_prompt()
            if line is None:
                break
            if not line.strip():
                continue
            await agent.send(line)
    finally:
        await agent.aclose()


if __name__ == "__main__":
    asyncio.run(main())
