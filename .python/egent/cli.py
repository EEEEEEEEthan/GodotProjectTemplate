"""egent 聊天 CLI。"""

from __future__ import annotations

import argparse
import asyncio
import sys

from openai import AsyncOpenAI

if __package__:
    from .conversation import Conversation, TextDelta
    from .model_settings import ConfigTemplateCreatedError, ModelSettings
else:
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
    from egent.conversation import Conversation, TextDelta
    from egent.model_settings import ConfigTemplateCreatedError, ModelSettings

DEFAULT_PROFILE = "coconut"
DEFAULT_MODEL = "low"
ASSISTANT_INSTRUCTIONS = "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。"


async def async_main(argv: list[str] | None = None) -> int:
    """解析 CLI 参数并运行交互式聊天，返回进程退出码。"""
    parser = argparse.ArgumentParser(description="egent 聊天")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    arguments = parser.parse_args(argv)
    try:
        settings = ModelSettings.load(arguments.profile, arguments.model)
    except (ConfigTemplateCreatedError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    conversation = Conversation(client, settings.model_name)
    conversation.add_message("system", ASSISTANT_INSTRUCTIONS)
    print(
        f"使用 [{settings.profile_name}] / {settings.model_alias} "
        f"→ {settings.model_name}\n",
    )
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


def main(argv: list[str] | None = None) -> None:
    """main"""
    raise SystemExit(asyncio.run(async_main(argv)))


if __name__ == "__main__":
    main()
