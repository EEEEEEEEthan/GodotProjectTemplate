"""共享 todo 列表工具 —— egent 与 nahte 跨会话追踪开发任务。

数据存储在 addons/egent/.data/todo.json 中，所有 agent 共享同一文件。
"""

from __future__ import annotations

import copy
import datetime
import json
import pathlib
import re
import typing

_DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / ".data"
_TODO_PATH = _DATA_DIR / "todo.json"

_EMPTY_DATA: dict[str, typing.Any] = {"next_id": 1, "items": []}


# ── 内部辅助 ──────────────────────────────────────────────


def _current_timestamp() -> str:
    """返回当前本地时区的 ISO 时间戳（精确到分钟）。"""
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(
        timespec="minutes"
    )


def _load_data() -> dict[str, typing.Any]:
    """从 todo.json 加载数据；文件不存在或格式异常时返回空结构。

    注意：必须返回全新的 dict/list，避免调用方意外修改模块级常量。
    """
    if not _TODO_PATH.is_file():
        return copy.deepcopy(_EMPTY_DATA)
    try:
        raw = _TODO_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return copy.deepcopy(_EMPTY_DATA)
        data = json.loads(raw)
        if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
            return copy.deepcopy(_EMPTY_DATA)
        return data
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(_EMPTY_DATA)


def _save_data(data: dict[str, typing.Any]) -> str | None:
    """将数据写回 todo.json；失败时返回错误信息。"""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _TODO_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return None
    except OSError as error:
        return f"错误：无法写入 todo 文件：{error}"


# ── 公开工具函数 ──────────────────────────────────────────


def add_item(  # pylint: disable=unused-argument
    agent_client: typing.Any, title: str, content: str
) -> str:
    """添加待办事项。

    @param title: 标题，不能为空
    @param content: 正文，不能为空
    """
    title_text = title.strip()
    if not title_text:
        return "错误：title 不能为空。"
    content_text = content.strip()
    if not content_text:
        return "错误：content 不能为空。"

    data = _load_data()
    item_id = data["next_id"]
    data["next_id"] += 1

    now = _current_timestamp()
    new_item = {
        "id": item_id,
        "title": title_text,
        "content": content_text,
        "created_at": now,
        "updated_at": now,
    }
    data["items"].append(new_item)

    save_error = _save_data(data)
    if save_error is not None:
        return save_error
    return f"已添加 todo #{item_id}「{title_text}」"


def remove_item(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any, id: int
) -> str:
    """删除待办事项。

    @param id: 待办事项 ID
    """
    data = _load_data()
    for i, item in enumerate(data["items"]):
        if item["id"] == id:
            title = item["title"]
            del data["items"][i]
            save_error = _save_data(data)
            if save_error is not None:
                return save_error
            return f"已删除 todo #{id}「{title}」"
    return f"错误：未找到 todo #{id}"


def update_item(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any, id: int, title: str, content: str
) -> str:
    """更新待办事项。

    @param id: 待办事项 ID
    @param title: 新标题，不能为空
    @param content: 新正文，不能为空
    """
    title_text = title.strip()
    if not title_text:
        return "错误：title 不能为空。"
    content_text = content.strip()
    if not content_text:
        return "错误：content 不能为空。"

    data = _load_data()
    for item in data["items"]:
        if item["id"] == id:
            item["title"] = title_text
            item["content"] = content_text
            item["updated_at"] = _current_timestamp()
            save_error = _save_data(data)
            if save_error is not None:
                return save_error
            return f"已更新 todo #{id}「{title_text}」"
    return f"错误：未找到 todo #{id}"


def list_items(  # pylint: disable=unused-argument
    agent_client: typing.Any
) -> str:
    """列出所有待办事项。"""
    data = _load_data()
    if not data["items"]:
        return "(无待办事项)"

    sorted_items = sorted(data["items"], key=lambda it: it["id"])
    lines = []
    for item in sorted_items:
        lines.append(f"#{item['id']} {item['title']} · {item['updated_at']}")
    return "\n".join(lines)


def get_item(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any, id: int
) -> str:
    """获取单个待办事项详情。

    @param id: 待办事项 ID
    """
    data = _load_data()
    for item in data["items"]:
        if item["id"] == id:
            return (
                f"ID：{item['id']}\n"
                f"标题：{item['title']}\n"
                f"正文：{item['content']}\n"
                f"创建时间：{item['created_at']}\n"
                f"更新时间：{item['updated_at']}"
            )
    return f"错误：未找到 todo #{id}"


def search_items(  # pylint: disable=unused-argument
    agent_client: typing.Any, query: str
) -> str:
    """在标题和正文中搜索待办事项。

    @param query: 搜索关键词（正则，忽略大小写）
    """
    query_text = query.strip()
    if not query_text:
        return "错误：query 不能为空。"

    try:
        regex = re.compile(query_text, re.IGNORECASE)
    except re.error as error:
        return f"错误：无效正则：{error}"

    data = _load_data()
    matches = []
    for item in data["items"]:
        if regex.search(item["title"]) or regex.search(item["content"]):
            matches.append(item)

    if not matches:
        return f"(无匹配「{query_text}」的待办事项)"

    matches.sort(key=lambda it: it["id"])
    lines = [f"#{it['id']} {it['title']}" for it in matches]
    return "\n".join(lines)
