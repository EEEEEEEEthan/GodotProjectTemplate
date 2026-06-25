"""工具输出长度限制。"""

from __future__ import annotations

MAX_OUTPUT_CHARS = 5000
_TRUNCATION_SUFFIX = "\n[内容太长被截断]"


def truncate_output(content: str) -> str:
    """截断过长输出并追加提示。"""
    if len(content) > MAX_OUTPUT_CHARS:
        return content[:MAX_OUTPUT_CHARS] + _TRUNCATION_SUFFIX
    return content
