"""控制台交互工具。"""

import sys


def read_prompt() -> str | None:
    """读取一行用户输入，EOF 时返回 None。"""
    sys.stdout.write("> ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n")
