"""egent 聊天 CLI。"""

from __future__ import annotations

import argparse
import asyncio
import sys

from agents import (
    Agent,
    RunConfig,
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_trace_processors,
    set_tracing_disabled,
)
from agents.models.openai_provider import OpenAIProvider
from openai import AsyncOpenAI

from .model_settings import ConfigTemplateCreatedError, ModelSettings

DEFAULT_PROFILE = "coconut"
DEFAULT_MODEL = "low"
ASSISTANT_INSTRUCTIONS = "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。"


async def async_main(argv: list[str] | None = None) -> int:
    """解析 CLI 参数并运行单 agent 交互式聊天，返回进程退出码。"""
    parser = argparse.ArgumentParser(description="egent 单 agent 聊天")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    arguments = parser.parse_args(argv)
    try:
        settings = ModelSettings.load(arguments.profile, arguments.model)
    except (ConfigTemplateCreatedError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    set_tracing_disabled(True)
    set_trace_processors([])
    client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url)
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")
    provider = OpenAIProvider(openai_client=client, use_responses=False)
    run_config = RunConfig(
        model=settings.model_name,
        model_provider=provider,
        tracing_disabled=True,
    )
    agent = Agent(
        name="助手",
        instructions=ASSISTANT_INSTRUCTIONS,
        model=settings.model_name,
    )
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
        result = await Runner.run(
            agent,
            user_message,
            run_config=run_config,
        )
        print(f"\n助手: {result.final_output or ''}\n")
    return 0


def main(argv: list[str] | None = None) -> None:
    """main"""
    raise SystemExit(asyncio.run(async_main(argv)))
