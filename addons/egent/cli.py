"""egent 聊天 CLI。"""

from __future__ import annotations

import argparse
import asyncio
import sys

from openai import AsyncOpenAI

if __package__:
    from .model_settings import ConfigTemplateCreatedError, ModelSettings
else:
    import pathlib

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
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
    messages: list[dict[str, str]] = [
        {"role": "system", "content": ASSISTANT_INSTRUCTIONS},
    ]
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
        messages.append({"role": "user", "content": user_message})
        print("\n助手: ", end="", flush=True)
        reply_parts: list[str] = []
        stream = await client.chat.completions.create(
            model=settings.model_name,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                reply_parts.append(delta)
                print(delta, end="", flush=True)
        print()
        messages.append({"role": "assistant", "content": "".join(reply_parts)})
    return 0


def main(argv: list[str] | None = None) -> None:
    """main"""
    raise SystemExit(asyncio.run(async_main(argv)))


if __name__ == "__main__":
    main()
