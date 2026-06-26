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


def resolve_directory(
    raw: str | None,
    *,
    label: str = "目录",
    default: str = ".",
    display: str | None = None,
) -> tuple[pathlib.Path | None, str | None]:
    """校验相对目录路径并解析为绝对路径；不存在或非目录时返回错误。"""
    directory_text = raw.strip() if raw else default
    relative_directory, directory_error = resolve_relative_path(
        directory_text,
        label=label,
    )
    if directory_error is not None:
        return None, directory_error

    root = (pathlib.Path.cwd() / relative_directory).resolve()
    if not root.is_dir():
        shown = display if display is not None else directory_text
        return None, f"错误：目录不存在：{shown}"
    return root, None
