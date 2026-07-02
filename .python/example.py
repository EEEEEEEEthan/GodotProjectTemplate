"""egent 聊天 CLI 示例。"""

from __future__ import annotations
import asyncio
from egent.conversation import Conversation, TextDelta, ToolCallExecuted
from egent import builtin_tools


async def async_main() -> int:
    """运行交互式聊天，返回进程退出码。"""
    conversation = Conversation("gpt5")
    conversation.add_message(
        "system",
        "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。"
        "需要查看项目目录结构时，调用 walk_files 工具。",
    )
    while True:
        try:
            user_message = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_message:
            continue
        conversation.add_message("user", user_message)
        async for event in conversation.request(tools=[builtin_tools.get_walk_file_tool()]):
            if isinstance(event, TextDelta):
                print(event.text, end="", flush=True)
            elif isinstance(event, ToolCallExecuted):
                print(
                    f"\n[工具 {event.name}]\n{event.result}\n",
                    flush=True,
                )
        print()
    return 0


def main() -> None:
    """main"""
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
