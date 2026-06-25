"""Ethan 交互式 REPL 入口。"""

import asyncio
import sys

import agent.agent_client
import agent.agent_events

__DIM = "\033[90m"
__RESET = "\033[0m"


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


async def main() -> None:
    """加载 agent 并循环处理用户消息与流式事件。"""
    client = agent.agent_client.AgentClient.load_agent("jason")
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
                    tool_header = (
                        f"[{event.name}]"
                        if not event.arguments
                        else f"[{event.name}] {event.arguments}"
                    )
                    write_line_colored(tool_header)
                    if event.result:
                        write_line_colored(event.result)
            sys.stdout.write("\n")
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
