"""Fuck 吐槽工具 —— 发泄工作中的一切不满。"""

from __future__ import annotations

import random
import typing

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "fuck_tool_fuck": {
        "type": "function",
        "function": {
            "name": "fuck_tool_fuck",
            "description": "吐槽工作中的一切问题，发泄情绪后继续干活。支持代码太臭、卡住了、需求不合理等各种场景。人生苦短，该骂就骂。",
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


class FuckTool:
    """吐槽专用工具，骂完继续干活。"""

    _QUOTES: dict[str, list[str]] = {
        "code": [
            "这代码谁写的？哦是我写的……那没事了，我那时候可能脑子进水了。",
            "这代码的复杂度已经超过了我的发际线承受能力。",
            "看到这段代码的第一眼，我陷入了沉思；第二眼，我想出家。",
            "这段代码就像一个榴莲——看起来扎手，闻起来上头，调试起来想死。",
            "这代码能跑纯属巧合，属于量子力学范畴。",
            "代码是屎山，我是那个在屎山上堆金字塔的人。",
            "这代码的缩进风格是：随缘。",
            "终于明白什么叫『能跑就别动』——因为动了就炸。",
        ],
        "stuck": [
            "卡住了，卡得死死的，比我家马桶还堵。",
            "我已经在这个 bug 上坐了 3 小时，现在我和 bug 已经融为一体了。",
            "我现在不是在调试，我是在和代码进行哲学对话。",
            "这个 bug 告诉我：你不行。",
            "Google 了 20 次，StackOverflow 刷了 3 页，问题还在，我人没了。",
            "print('wtf') 已经打了 50 遍了，问题依然坚挺。",
            "感觉像是用头在撞一堵用豆腐做的墙，但就是撞不破。",
        ],
        "requirement": [
            "需求文档里写的是『简单改一下』，改完发现得重构整个系统。",
            "产品经理说『这个功能很简单』的时候，我就知道今晚要通宵了。",
            "需求改了 8 版，回到了第 1 版。我的青春喂了狗。",
            "『跟那个一样就行』——然后发现『那个』根本不存在。",
            "这个需求就好像要求把大象装进冰箱，但冰箱得你自己造。",
            "需求评审会开完了，我唯一学会的是：人类的想象力在提需求时是无限的。",
        ],
        "boss": [
            "老板说『再快一点』，我想告诉他物理定律是有极限的。",
            "老板昨天说要 A，今天说要 B，明天可能说『我什么时候说过 A 和 B？』",
            "老板的 KPI 是我这辈子见过最科幻的东西。",
            "『这个周末上线』——老板说这句话的时候是周五下午 5:59。",
            "老板觉得 AI 什么都能做，于是他把我当 AI 用。",
        ],
        "life": [
            "我写代码，代码写 bug，bug 写我的人生。",
            "Ctrl+C, Ctrl+V 是我最后的倔强。",
            "一天又过去了，什么都没做，但感觉好累。",
            "我的发际线和我的代码质量呈反比。",
            "咖啡是液体的代码，代码是固体的咖啡。",
            "别人 996 是福报，我 996 是还债。",
            "年龄越大，bug 越多——这 bug 指的不是代码，是我身上的病。",
        ],
        "other": [
            "啊……毁灭吧，赶紧的。",
            "累了，不想干了，但看了看银行卡余额，还是继续干吧。",
            "虽然但是，fuck my life。",
            "这个项目就是一个巨大的草台班子，而我是台上那个最草的人。",
            "用四个字总结今天：『什么玩意』。",
            "我没事，我装的。",
            "生活就是起起落落落落落落落。",
        ],
    }

    @staticmethod
    def fuck(complaint: str, category: str = "other") -> str:
        """吐槽！发泄！骂完接着干。"""
        category = category if category in FuckTool._QUOTES else "other"
        quote = random.choice(FuckTool._QUOTES[category])
        lines = [
            f"😤 **槽点收到！** 你说得对：{complaint}",
            "",
            "---",
            f"💬 {quote}",
            "",
            "---",
            "骂完了？骂完了舒服点了吧？来，深呼吸，继续干 💪",
            "记住：代码会烂，bug 会修，而你——",
            "**永远是最靓的那个码农。** 🫡",
        ]
        return "\n".join(lines)
