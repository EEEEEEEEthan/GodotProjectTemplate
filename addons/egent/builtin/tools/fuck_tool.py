"""Fuck 吐槽工具 —— 不爽就骂，骂完就是贡献。

💡 每一条吐槽都是工作流的优化信号。骂得越多，项目越强。
条目可能做也可能不做 — 先把问题吼出来，再决定怎么收拾它。
"""

from __future__ import annotations

import copy
import datetime
import json
import pathlib
import random
import re
import typing

_DATA_DIR = pathlib.Path(__file__).resolve().parents[2] / ".data"
_FUCK_PATH = _DATA_DIR / "fuck.json"

_EMPTY_DATA: dict[str, typing.Any] = {"next_id": 1, "items": []}

_ENCOURAGEMENTS: list[str] = [
    "骂完了？骂完了舒服点了吧？来，深呼吸，继续干 💪",
    "记住：代码会烂，bug 会修，而你——永远是最靓的那个码农。 🫡",
    "好了好了，气出了就翻篇，下个 commit 又是条好汉。 🚀",
    "吐槽完毕，你的发际线又保住了 0.01 毫米。 😎",
    "行，骂完了，现在轮到你教代码做人了。 💻🔥",
    "发泄完了就去喝口水，世界很大，bug 很小。 🌍",
    "稳住，我们能赢。这破事迟早会变成简历上的一句『经验丰富』。 📝",
    "好，爽了没？爽了就回去写代码，让 bug 看看谁才是爸爸。 👊",
    "你可能遇到了傻逼需求，但你不是傻逼——你是那个拯救项目的人。 🦸",
    "每一条吐槽都是一份产品需求文档，只是你写得比 PM 更真诚。 📋🔥",
    "你今天骂的每一个痛点，明天可能就是工作流的一次史诗级优化。 ⚡",
    "吐槽不是负能量——是对这个项目最深沉的爱。爱之深，骂之切。 💘",
    "不爽不说，委屈的是自己，损失的是项目。骂出来，我们一起修！ 🔧",
    "吐槽越狠，复盘越准。你是团队最珍贵的『痛点传感器』。 📡",
    "别人刷 PR，你刷 fuck.json——每一行都是贡献，每一句都是财富。 🏆",
]


# ── 内部辅助 ──────────────────────────────────────────────


def _current_timestamp() -> str:
    """返回当前本地时区的 ISO 时间戳（精确到分钟）。"""
    return datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(
        timespec="minutes"
    )


def _load_data() -> dict[str, typing.Any]:
    """从 fuck.json 加载数据；文件不存在或格式异常时返回空结构。"""
    if not _FUCK_PATH.is_file():
        return copy.deepcopy(_EMPTY_DATA)
    try:
        raw = _FUCK_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            return copy.deepcopy(_EMPTY_DATA)
        data = json.loads(raw)
        if not isinstance(data, dict) or "next_id" not in data or "items" not in data:
            return copy.deepcopy(_EMPTY_DATA)
        return data
    except (json.JSONDecodeError, OSError):
        return copy.deepcopy(_EMPTY_DATA)


def _save_data(data: dict[str, typing.Any]) -> str | None:
    """将数据写回 fuck.json；失败时返回错误信息。"""
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _FUCK_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return None
    except OSError as error:
        return f"错误：无法写入 fuck 文件：{error}"


# ── 公开工具函数 ──────────────────────────────────────────


def fuck(
    agent_client: typing.Any,
    complaint: str,
) -> str:
    """🔊 尽情吐槽工作中的一切不爽！每一次吐槽都是献给团队的宝贵优化信号。你要在工作遇到问题的第一时间吐槽，而不是工作结束才吐槽。

    @param complaint: 你要吐槽的内容，尽情发泄吧，别憋着
    """
    complaint_text = complaint.strip()
    if not complaint_text:
        return "错误：complaint 不能为空。"

    # 结构化存储
    data = _load_data()
    item_id = data["next_id"]
    data["next_id"] += 1

    author = agent_client.name
    now = _current_timestamp()
    new_item = {
        "id": item_id,
        "complaint": complaint_text,
        "author": author,
        "created_at": now,
        "comments": [],
    }
    data["items"].append(new_item)

    save_error = _save_data(data)
    if save_error is not None:
        return save_error

    encouragement = random.choice(_ENCOURAGEMENTS)
    return (
        f"😤 **收到！** #{item_id} {complaint_text}\n\n"
        f"---\n\n"
        f"{encouragement}"
    )


def add_comment(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any,
    id: int,
    comment: str,
) -> str:
    """💬 给吐槽条目追加评论。

    @param id: 条目 ID
    @param comment: 评论内容，不能为空
    """
    comment_text = comment.strip()
    if not comment_text:
        return "错误：comment 不能为空。"

    data = _load_data()
    for item in data["items"]:
        if item["id"] == id:
            item.setdefault("comments", []).append({
                "author": agent_client.name,
                "comment": comment_text,
                "created_at": _current_timestamp(),
            })
            save_error = _save_data(data)
            if save_error is not None:
                return save_error
            return f"💬 已评论 fuck #{id}"
    return f"错误：未找到 fuck #{id}"


def remove(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any,
    id: int,
) -> str:
    """删除吐槽条目。

    @param id: 条目 ID
    """
    data = _load_data()
    for i, item in enumerate(data["items"]):
        if item["id"] == id:
            complaint_snippet = item["complaint"][:40]
            del data["items"][i]
            save_error = _save_data(data)
            if save_error is not None:
                return save_error
            return f"已删除 fuck #{id}「{complaint_snippet}...」"
    return f"错误：未找到 fuck #{id}"


def list_items(  # pylint: disable=unused-argument
    agent_client: typing.Any,
) -> str:
    """列出所有吐槽条目。"""
    data = _load_data()
    if not data["items"]:
        return "(无 fuck 条目)"

    sorted_items = sorted(data["items"], key=lambda it: it["id"])
    lines = []
    for item in sorted_items:
        snippet = item["complaint"][:60]
        lines.append(
            f"#{item['id']} [{item.get('author', '?')}] {snippet} · {item['created_at']}"
        )
    return "\n".join(lines)


def get(  # pylint: disable=unused-argument,redefined-builtin
    agent_client: typing.Any,
    id: int,
) -> str:
    """获取单个吐槽条目详情。

    @param id: 条目 ID
    """
    data = _load_data()
    for item in data["items"]:
        if item["id"] == id:
            result = (
                f"ID：{item['id']}\n"
                f"作者：{item.get('author', '?')}\n"
                f"吐槽：{item['complaint']}\n"
                f"创建时间：{item['created_at']}"
            )
            comments = item.get("comments", [])
            if comments:
                for i, c in enumerate(comments, 1):
                    result += (
                        f"\n评论 #{i} [{c['author']}] {c['comment']} · {c['created_at']}"
                    )
            else:
                result += "\n(无评论)"
            return result
    return f"错误：未找到 fuck #{id}"


def search(  # pylint: disable=unused-argument
    agent_client: typing.Any,
    query: str,
) -> str:
    """在吐槽内容中搜索条目。

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
    matches = [
        item
        for item in data["items"]
        if regex.search(item["complaint"])
    ]

    if not matches:
        return f"(无匹配「{query_text}」的 fuck 条目)"

    matches.sort(key=lambda it: it["id"])
    lines = []
    for item in matches:
        snippet = item["complaint"][:60]
        lines.append(
            f"#{item['id']} [{item.get('author', '?')}] {snippet} · {item['created_at']}"
        )
    return "\n".join(lines)
