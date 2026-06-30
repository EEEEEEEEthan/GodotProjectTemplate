"""路径校验：仅接受相对工作目录的路径。"""

from __future__ import annotations

import fnmatch
import pathlib


def normalize_path_pattern(pattern: str) -> str:
    """规范化 ignore / no_write 路径模式。"""
    return pattern.replace("\\", "/").strip().lstrip("/")


def matches_path_rule(relative_path: pathlib.PurePath, pattern: str) -> bool:
    """判断相对路径是否命中 ignore / no_write 规则。

    - 含 `/` 的模式：按路径前缀或 fnmatch 全路径匹配（如 `addons/egent`、`addons/egent/*`）
    - 单段模式：对任一路径段做 fnmatch（如 `.git`、`*.pyc`）
    """
    normalized_pattern = normalize_path_pattern(pattern)
    if not normalized_pattern:
        return False

    rel_posix = relative_path.as_posix()

    if "/" in normalized_pattern:
        prefix = normalized_pattern.removesuffix("/*").removesuffix("/")
        if rel_posix == prefix or rel_posix.startswith(f"{prefix}/"):
            return True
        pattern_parts = pathlib.PurePosixPath(prefix).parts
        path_parts = relative_path.parts
        for index in range(len(path_parts) - len(pattern_parts) + 1):
            if path_parts[index : index + len(pattern_parts)] == pattern_parts:
                return True
        return fnmatch.fnmatch(rel_posix, normalized_pattern)

    return any(
        fnmatch.fnmatch(segment, normalized_pattern)
        for segment in relative_path.parts
    )


def is_ignored_relative_path(
    relative_path: str | pathlib.PurePath,
    patterns: tuple[str, ...] | list[str],
) -> bool:
    """相对路径是否应被 ignore / no_write 规则跳过。"""
    path = pathlib.PurePosixPath(str(relative_path).replace("\\", "/"))
    return any(matches_path_rule(path, pattern) for pattern in patterns)


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
