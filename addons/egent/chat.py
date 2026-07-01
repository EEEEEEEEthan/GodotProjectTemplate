"""交互式单 agent 聊天。"""

from __future__ import annotations

import argparse
import asyncio
import pathlib
import sys

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
ADDONS_ROOT = PACKAGE_ROOT.parent
if str(ADDONS_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDONS_ROOT))

from agents import SQLiteSession

from egent.conversation import Conversation, ModelConfig, ModelRuntime, create_assistant_agent

DEFAULT_DATA_DIR = PACKAGE_ROOT / ".data"
DEFAULT_SESSION_DATABASE = DEFAULT_DATA_DIR / "conversations.db"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="egent 单 agent 聊天")
    parser.add_argument(
        "--config",
        type=pathlib.Path,
        default=PACKAGE_ROOT / "model.toml",
        help="模型配置文件路径",
    )
    parser.add_argument(
        "--session-id",
        default="default",
        help="会话 ID，用于持久化上下文",
    )
    return parser


async def chat_loop(conversation: Conversation) -> None:
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
        reply = await conversation.send(user_message)
        print(f"\n助手: {reply}\n")


async def async_main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)
    try:
        config = ModelConfig.load(arguments.config)
    except FileNotFoundError as error:
        example_path = PACKAGE_ROOT / "model.example.toml"
        print(f"{error}", file=sys.stderr)
        print(f"可复制 {example_path} 为 {arguments.config}", file=sys.stderr)
        return 1
    model_runtime = ModelRuntime.from_config(config)
    agent = create_assistant_agent(model_runtime)
    DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = SQLiteSession(arguments.session_id, DEFAULT_SESSION_DATABASE)
    conversation = Conversation(agent, model_runtime, session=session)
    await chat_loop(conversation)
    return 0


def main(argv: list[str] | None = None) -> None:
    raise SystemExit(asyncio.run(async_main(argv)))


if __name__ == "__main__":
    main()
