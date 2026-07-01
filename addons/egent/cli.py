"""egent 聊天 CLI。"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import sys
import tomllib

from agents import (
    Agent,
    RunConfig,
    Runner,
    SQLiteSession,
    set_default_openai_api,
    set_default_openai_client,
    set_trace_processors,
    set_tracing_disabled,
)
from agents.models.openai_provider import OpenAIProvider
from openai import AsyncOpenAI

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = PACKAGE_ROOT / ".model.toml"
DEFAULT_SESSION_DATABASE = PACKAGE_ROOT / ".data" / "conversations.db"
DEFAULT_PROFILE = "coconut"
DEFAULT_MODEL = "low"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
RESERVED_PROFILE_KEYS = frozenset({"key", "url"})
ASSISTANT_INSTRUCTIONS = "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。"

MODEL_CONFIG_TEMPLATE = """\
[coconut]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"

[openai]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"

[vocal]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"
"""


class ConfigTemplateCreatedError(FileNotFoundError):
    """配置文件已自动创建，需用户填写后重试。"""


def load_model_settings(
    profile_name: str,
    model_alias: str,
) -> tuple[str, str, str, str, str]:
    """加载 API key、base URL、模型名，以及配置节与模型别名。"""
    config_path = DEFAULT_CONFIG_PATH
    if not config_path.is_file():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(MODEL_CONFIG_TEMPLATE, encoding="utf-8")
        raise ConfigTemplateCreatedError(
            f"已创建配置模板 {config_path}，请填写后重新运行",
        )
    with config_path.open("rb") as config_file:
        profiles = tomllib.load(config_file)
    profile = profiles.get(profile_name)
    if not isinstance(profile, dict):
        available_profiles = [
            name for name, data in profiles.items() if isinstance(data, dict)
        ]
        raise ValueError(
            f"未知配置节 {profile_name!r}，可选: {available_profiles}",
        )
    model_aliases = [
        field_name
        for field_name in profile
        if field_name not in RESERVED_PROFILE_KEYS
    ]
    if model_alias not in model_aliases:
        raise ValueError(
            f"配置节 [{profile_name}] 不存在模型别名 {model_alias!r}，"
            f"可选: {model_aliases}",
        )
    model_name = profile[model_alias]
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError(
            f"配置节 [{profile_name}] 模型别名 {model_alias!r} 的模型名为空",
        )
    base_url = profile.get("url", DEFAULT_BASE_URL)
    if not isinstance(base_url, str) or not base_url.strip():
        base_url = DEFAULT_BASE_URL
    api_key = profile.get("key")
    if not isinstance(api_key, str) or not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            f"配置节 [{profile_name}] 未设置 key，"
            f"请在 .model.toml 或环境变量 OPENAI_API_KEY 中配置",
        )
    return (
        api_key,
        base_url,
        model_name.strip(),
        profile_name,
        model_alias,
    )


def create_run_config(api_key: str, base_url: str, model: str) -> RunConfig:
    """初始化 OpenAI 客户端并返回 RunConfig。"""
    set_tracing_disabled(True)
    set_trace_processors([])
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")
    provider = OpenAIProvider(openai_client=client, use_responses=False)
    return RunConfig(
        model=model,
        model_provider=provider,
        tracing_disabled=True,
    )


async def async_main(argv: list[str] | None = None) -> int:
    """解析参数并进入聊天循环。"""
    parser = argparse.ArgumentParser(description="egent 单 agent 聊天")
    parser.add_argument("--profile", default=DEFAULT_PROFILE)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--session-id", default="default")
    arguments = parser.parse_args(argv)
    try:
        api_key, base_url, resolved_model, profile_name, model_alias = (
            load_model_settings(arguments.profile, arguments.model)
        )
    except (ConfigTemplateCreatedError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    run_config = create_run_config(api_key, base_url, resolved_model)
    agent = Agent(
        name="助手",
        instructions=ASSISTANT_INSTRUCTIONS,
        model=resolved_model,
    )
    print(f"使用 [{profile_name}] / {model_alias} → {resolved_model}\n")
    print("输入消息开始对话，输入 exit / quit 退出。\n")
    DEFAULT_SESSION_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    session = SQLiteSession(arguments.session_id, DEFAULT_SESSION_DATABASE)
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
            session=session,
        )
        print(f"\n助手: {result.final_output or ''}\n")
    return 0


def main(argv: list[str] | None = None) -> None:
    """CLI 同步入口。"""
    raise SystemExit(asyncio.run(async_main(argv)))
