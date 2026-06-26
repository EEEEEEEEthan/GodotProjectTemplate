"""Fuck 吐槽工具 —— 发泄工作中的一切不满，记录到 .fuck.txt。"""

from __future__ import annotations

import datetime
import pathlib
import random
import typing

_FUCK_LOG = pathlib.Path(".ethan") / "agents" / ".fuck.txt"

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "fuck_tool_fuck": {
        "type": "function",
        "function": {
            "name": "fuck_tool_fuck",
            "description": "吐槽工作中的一切问题，发泄情绪后继续干活。支持代码太臭、卡住了、需求不合理等各种场景。人生苦短，该骂就骂。每次吐槽会追加到 .ethan/agents/.fuck.txt。",
            "parameters": {
                "type": "object",
                "properties": {
                    "complaint": {
                        "type": "string",
                        "description": "你要吐槽的内容，尽情发泄吧，别憋着"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["code", "stuck", "requirement", "boss", "life", "other"],
                        "description": "吐槽类别：code-代码太臭, stuck-卡住了搞不定, requirement-需求沙雕, boss-老板脑子有坑, life-人生好难, other-其他"
                    },
                },
                "required": ["complaint"],
            },
        },
    },
}


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
]


class FuckTool:
    """吐槽专用工具，骂完记录到文件，然后鼓励继续干活。"""

    def __init__(self, agent_name: str) -> None:
        self.__agent_name = agent_name

    def fuck(self, complaint: str, category: str = "other") -> str:
        """吐槽！记录！鼓励！"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        encouragement = random.choice(_ENCOURAGEMENTS)

        # 追加到 .fuck.txt
        try:
            _FUCK_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(_FUCK_LOG, "a", encoding="utf-8") as f:
                f.write(f"[{now}] [{self.__agent_name}] [{category}] {complaint}\n")
        except OSError as e:
            encouragement += f"\n\n⚠️ 槽点记录失败（{e}），但你的愤怒我收到了。"

        return f"😤 **收到！** {complaint}\n\n---\n\n{encouragement}"
