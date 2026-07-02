"""egent 聊天 CLI 示例。"""

from __future__ import annotations

import asyncio
import pathlib
import sys

from openai import AsyncOpenAI

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from egent.conversation import Conversation, TextDelta
from egent.model_settings import ConfigTemplateCreatedError, ModelSettings


async def async_main() -> int:
    """运行交互式聊天，返回进程退出码。"""
    # 示例脚本：profile 与 system prompt 刻意硬编码，比抽常量更直观。
    try:
        settings = ModelSettings.load("gpt5")  # noqa: S1192
    except (ConfigTemplateCreatedError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    conversation = Conversation(client, settings.model_name)
    conversation.add_message(
        "system",
        "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。",  # noqa: S1192
    )
    print(f"使用 [{settings.profile_name}] → {settings.model_name}\n")
    print("输入消息开始对话，输入 exit / quit 退出。\n")
    while True:
        try:
            user_message = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit", "/exit"}:
            break
        print("\n助手: ", end="", flush=True)
        conversation.add_message("user", user_message)
        async for event in conversation.send():
            if isinstance(event, TextDelta):
                print(event.text, end="", flush=True)
        print()
    return 0


def main() -> None:
    """main"""
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()
