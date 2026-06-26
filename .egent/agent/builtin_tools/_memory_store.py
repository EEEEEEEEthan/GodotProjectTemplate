"""记忆存储内部模块。"""

from __future__ import annotations

import datetime
import pathlib
import re
import typing

import agent.data_loader

RELIABILITY_NOTICE = (
    "记忆由过往对话沉淀，未必准确；读取、引用或更新前请结合当前代码与事实自行核实。"
)
_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_ENTRY_HEADER = re.compile(r"^## (.+?) · (.+)\s*$")
_DISPLAY_TIME_FORMAT = "%Y-%m-%d %H:%M"


class MemoryItem(typing.TypedDict):
    """单条记忆的正文与更新时间。"""

    value: str
    updated_at: str


def storage_path(agent_name: str) -> pathlib.Path:
    """返回指定 agent 的记忆文件绝对路径。"""
    safe_name, error = sanitize_agent_name(agent_name)
    if error is not None:
        raise ValueError(error)
    return (agent.data_loader.EGENT_ROOT / "agents" / safe_name / ".memory.txt").resolve()


def current_timestamp() -> str:
    """返回当前本地时区的 ISO 时间戳（精确到分钟）。"""
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="minutes")


def create_memory_item(value: str) -> MemoryItem:
    """用给定正文创建带当前时间戳的记忆条目。"""
    return MemoryItem(value=value, updated_at=current_timestamp())


def format_updated_at(timestamp: str) -> str:
    """将 ISO 时间戳格式化为可读时间；无法解析时原样返回。"""
    if not timestamp:
        return "未知"
    try:
        moment = datetime.datetime.fromisoformat(timestamp)
        return moment.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return timestamp


def sort_items_by_updated_at(items: dict[str, MemoryItem]) -> list[tuple[str, MemoryItem]]:
    """按更新时间升序排列记忆条目。"""
    return sorted(items.items(), key=lambda pair: pair[1]["updated_at"] or "")


def load_items(agent_name: str) -> dict[str, MemoryItem]:
    """从磁盘加载 agent 的全部记忆条目。"""
    path = storage_path(agent_name)
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    if not text:
        return {}
    if not text.startswith("## "):
        return {}
    items: dict[str, MemoryItem] = {}
    for block in re.split(r"\n(?=## )", text):
        block = block.strip()
        if not block:
            continue
        lines = block.split("\n", 1)
        header_match = _ENTRY_HEADER.match(lines[0])
        if header_match is None:
            continue
        title = header_match.group(1).strip()
        updated_at = _parse_display_time(header_match.group(2).strip())
        value = lines[1].lstrip("\n") if len(lines) > 1 else ""
        items[title] = MemoryItem(value=value, updated_at=updated_at)
    return items


def save_items(items: dict[str, MemoryItem], agent_name: str) -> str | None:
    """将记忆条目写回磁盘；失败时返回错误信息。"""
    path = storage_path(agent_name)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        parts = [
            f"## {title} · {format_updated_at(item['updated_at'])}\n\n{item['value']}"
            for title, item in sort_items_by_updated_at(items)
        ]
        path.write_text(
            ("\n\n".join(parts) + "\n") if parts else "",
            encoding="utf-8",
            newline="",
        )
    except OSError as error:
        return f"错误：无法写入记忆文件：{error}"
    return None


def find_key(items: dict[str, MemoryItem], key: str) -> str | None:
    """按标题大小写不敏感查找已有键，未找到返回 None。"""
    normalized = key.strip()
    if not normalized:
        return None
    for existing in items:
        if existing.casefold() == normalized.casefold():
            return existing
    return None


def validate_key(key: str, *, label: str = "key") -> tuple[str | None, str | None]:
    """校验记忆标题非空。"""
    normalized = key.strip()
    if not normalized:
        return None, f"错误：{label} 不能为空。"
    return normalized, None


def validate_value(value: str | None, *, label: str = "value") -> tuple[str | None, str | None]:
    """校验记忆正文非空。"""
    if value is None or len(value) == 0:
        return None, f"错误：{label} 不能为空。"
    return value, None


def compile_ignore_case_regex(pattern: str) -> tuple[re.Pattern[str] | None, str | None]:
    """编译忽略大小写的正则。"""
    try:
        return re.compile(pattern, re.IGNORECASE), None
    except re.error as error:
        return None, f"错误：无效正则：{error}"


def sanitize_agent_name(agent_name: str) -> tuple[str, str | None]:
    """校验并清理 agent 名称。"""
    text = agent_name.strip()
    if not text:
        return "", "错误：agent 名称不能为空。"
    sanitized = _INVALID_FILENAME_CHARS.sub("_", text).strip(". ")
    if not sanitized:
        return "", "错误：agent 名称无效。"
    return sanitized, None


def _parse_display_time(display: str) -> str:
    if not display or display == "未知":
        return ""
    try:
        moment = datetime.datetime.strptime(display, _DISPLAY_TIME_FORMAT)
        moment = moment.replace(tzinfo=datetime.datetime.now().astimezone().tzinfo)
        return moment.isoformat(timespec="minutes")
    except ValueError:
        pass
    try:
        datetime.datetime.fromisoformat(display)
        return display
    except ValueError:
        return ""
