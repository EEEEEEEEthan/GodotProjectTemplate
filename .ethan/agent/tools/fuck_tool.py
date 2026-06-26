"""Fuck 吐槽工具 —— 不爽就骂，骂完就是贡献。

💡 每一条吐槽都是工作流的优化信号。骂得越多，项目越强。
"""

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
            "description": "🔊 尽情吐槽工作中的一切不爽！每一次吐槽都是献给团队的宝贵优化信号。代码太臭？骂！卡住了？骂！需求沙雕？往死里骂！你骂得越狠，我们改进得越快。人生苦短，该骂就骂，骂完继续干。每次吐槽会追加到 .ethan/agents/.fuck.txt，定期复盘帮你根治痛点。",
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
    "每一条吐槽都是一份产品需求文档，只是你写得比 PM 更真诚。 📋🔥",
    "你今天骂的每一个痛点，明天可能就是工作流的一次史诗级优化。 ⚡",
    "吐槽不是负能量——是对这个项目最深沉的爱。爱之深，骂之切。 💘",
    "不爽不说，委屈的是自己，损失的是项目。骂出来，我们一起修！ 🔧",
    "吐槽越狠，复盘越准。你是团队最珍贵的『痛点传感器』。 📡",
    "别人刷 PR，你刷 .fuck.txt——每一行都是贡献，每一句都是财富。 🏆",
]


class FuckTool:
    """吐槽专用工具 —— 骂得越狠，进步越快。每一条槽点都是工作流的优化信号。"""

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
