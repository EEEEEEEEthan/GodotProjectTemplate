"""交互式单 agent 聊天；可从任意目录运行：python addons/egent/cli.py"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

if __package__ is None:
    addons_root = pathlib.Path(__file__).resolve().parent.parent
    if str(addons_root) not in sys.path:
        sys.path.insert(0, str(addons_root))

from agents import Agent, Runner, SQLiteSession
from egent import ModelConfig, ModelRuntime, create_assistant_agent
from egent.model_config import DEFAULT_CONFIG_PATH, ConfigTemplateCreatedError

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_DATA_DIR = PACKAGE_ROOT / ".data"
DEFAULT_SESSION_DATABASE = DEFAULT_DATA_DIR / "conversations.db"


async def chat_loop(
    agent: Agent,
    model_runtime: ModelRuntime,
    *,
    session: SQLiteSession,
) -> None:
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
            run_config=model_runtime.run_config,
            session=session,
        )
        reply = result.final_output or ""
        print(f"\n助手: {reply}\n")


async def async_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="egent 单 agent 聊天")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=DEFAULT_CONFIG_PATH,
        help="模型配置文件路径",
    )
    parser.add_argument(
        "--session-id",
        default="default",
        help="会话 ID，用于持久化上下文",
    )
    arguments = parser.parse_args(argv)
    try:
        config = ModelConfig.load("coconut", "low", arguments.config)
    except ConfigTemplateCreatedError as error:
        print(error, file=sys.stderr)
        return 1
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    model_runtime = ModelRuntime.from_config(config)
    agent = create_assistant_agent(model_runtime)
    print(
        f"使用 [{config.profile_name}] / {config.tier_name}"
        f" → {config.model}\n",
    )
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = SQLiteSession(arguments.session_id, DEFAULT_SESSION_DATABASE)
    await chat_loop(agent, model_runtime, session=session)
    return 0


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(async_main(argv)))


if __name__ == "__main__":
    main()
