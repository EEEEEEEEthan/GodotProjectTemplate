"""路径校验：仅接受相对工作目录的路径。"""

from __future__ import annotations

import pathlib


def resolve_relative_path(
    raw: str,
    *,
    label: str = "路径",
) -> tuple[pathlib.Path | None, str | None]:
    """校验并返回相对工作目录的路径；非法时返回错误信息。"""
    text = raw.strip() if raw else ""
    if not text:
        return None, f"错误：{label}不能为空"
    path = pathlib.Path(text)
    if path.is_absolute():
        return (
            None,
            f"错误：{label}必须是相对工作目录的路径，不接受绝对路径：{raw}",
        )
    return path, None
