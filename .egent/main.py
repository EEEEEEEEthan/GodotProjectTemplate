"""Egent 交互式 REPL 入口。"""

import argparse
import asyncio
import sys

import httpx
import openai

import agent.agent_client
import agent.agent_events
import agent.agent_tools
import agent_config
import tool_handlers

__DIM = "\033[90m"
__RESET = "\033[0m"


def _build_agent_client(name: str) -> agent.agent_client.AgentClient:
    """从 agent_config 构造单个 AgentClient 并绑定工具。"""
    client = agent.agent_client.AgentClient.load_agent(name)
    client.tools = tool_handlers.get_all_tools(client)
    return client


AGENT_CLIENTS: dict[str, agent.agent_client.AgentClient] = {
    name: _build_agent_client(name) for name in agent_config.AGENTS
}


def read_prompt() -> str | None:
    """读取一行用户输入，EOF 时返回 None。"""
    sys.stdout.write("> ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n")


def write_line_colored(value: str, *, dim: bool = True) -> None:
    """向 stdout 输出一行，可选灰色。"""
    if dim:
        sys.stdout.write(f"{__DIM}{value}{__RESET}\n")
    else:
        sys.stdout.write(f"{value}\n")


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


def format_tool_header(
    event: agent.agent_events.ToolInvoked,
    *,
    debug: bool,
) -> str:
    """按调试模式格式化工具调用摘要行。"""
    if debug:
        arguments_text = agent.agent_tools.format_tool_arguments(event.arguments)
    else:
        arguments_text = agent.agent_tools.format_tool_arguments_brief(event.arguments)
    if not arguments_text:
        return f"[{event.name}]"
    return f"[{event.name}] {arguments_text}"


async def main() -> None:
    """加载 agent 并循环处理用户消息与流式事件。"""
    args = parse_args()
    client = AGENT_CLIENTS.get(args.agent)
    if client is None:
        known = ", ".join(sorted(AGENT_CLIENTS))
        write_line_colored(f"未知 Agent：{args.agent}（可用：{known}）", dim=False)
        return
    try:
        await client.prepare()
        write_line_colored(f"@{client.name}, {client.model}, {client.base_url}")
        tool_lines = ["loading tools..."] + [f"  - {tool}" for tool in client.tool_whitelist]
        write_line_colored("\n".join(tool_lines))
        write_line_colored(f"{client.system_prompt}")
        while True:
            line = read_prompt()
            if line is None:
                break
            if not line.strip():
                continue
            try:
                async for event in client.send("user", line):
                    if isinstance(event, agent.agent_events.TextDelta):
                        sys.stdout.write(event.text)
                        sys.stdout.flush()
                    elif isinstance(event, agent.agent_events.ToolInvoked):
                        try:
                            if sys.stdout.isatty():
                                sys.stdout.write("\n")
                        except OSError:
                            pass
                        write_line_colored(
                            format_tool_header(event, debug=args.debug)
                        )
                        if args.debug and event.result:
                            write_line_colored(event.result)
            except agent.agent_client.STREAM_RETRYABLE_ERRORS as error:
                write_line_colored(
                    f"API 连接中断（已重试仍失败）: {error}",
                    dim=False,
                )
            except openai.APIError as error:
                write_line_colored(f"API 错误: {error}", dim=False)
            sys.stdout.write("\n")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
