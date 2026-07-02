"""egent 聊天 CLI 示例。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from egent.conversation import Conversation, TextDelta, ToolCallExecuted
from egent.model_settings import ConfigTemplateCreatedError, ModelSettings

IGNORED_DIRECTORY_NAMES = frozenset({
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
})


def list_file_tree(directory_path: str = ".", max_depth: int = 3) -> str:
    """列出指定目录下的文件树结构。

    @param directory_path 要列出的目录路径，相对或绝对均可。
    @param max_depth 目录展开的最大深度，范围 1-8。
    """
    root_directory = Path(directory_path).resolve()
    if not root_directory.exists():
        return f"目录不存在: {root_directory}"
    if not root_directory.is_dir():
        return f"路径不是目录: {root_directory}"

    lines = [f"{root_directory.name}/"]
    lines.extend(
        _build_directory_lines(
            directory=root_directory,
            prefix="",
            current_depth=1,
            max_depth=max_depth,
        ),
    )
    return "\n".join(lines)


def _build_directory_lines(
    *,
    directory: Path,
    prefix: str,
    current_depth: int,
    max_depth: int,
) -> list[str]:
    if current_depth > max_depth:
        return []

    entries = sorted(
        (
            entry
            for entry in directory.iterdir()
            if entry.name not in IGNORED_DIRECTORY_NAMES
        ),
        key=lambda entry: (entry.is_file(), entry.name.lower()),
    )
    lines: list[str] = []
    for index, entry in enumerate(entries):
        is_last_entry = index == len(entries) - 1
        branch = "└── " if is_last_entry else "├── "
        child_prefix = prefix + ("    " if is_last_entry else "│   ")
        if entry.is_dir():
            lines.append(f"{prefix}{branch}{entry.name}/")
            lines.extend(
                _build_directory_lines(
                    directory=entry,
                    prefix=child_prefix,
                    current_depth=current_depth + 1,
                    max_depth=max_depth,
                ),
            )
        else:
            lines.append(f"{prefix}{branch}{entry.name}")
    return lines


async def async_main() -> int:
    """运行交互式聊天，返回进程退出码。"""
    try:
        settings = ModelSettings.load("gpt5")  # noqa: S1192
    except (ConfigTemplateCreatedError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    conversation = Conversation(settings)
    conversation.add_message(
        "system",
        "你是一个有用的 AI 助手。回答要准确、简洁；不确定时明确说明。"  # noqa: S1192
        "需要查看项目目录结构时，调用 list_file_tree 工具。",
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
        async for event in conversation.request(tools=[list_file_tree]):
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
