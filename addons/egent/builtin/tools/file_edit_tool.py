"""文件编辑工具：创建文件、删除文件与替换文本。"""

from __future__ import annotations

import pathlib
import typing

from . import _path_util


def _resolve_writable_file(
    agent_client: typing.Any,
    file_path: str,
    *,
    must_exist: bool,
) -> tuple[pathlib.Path | None, str | None]:
    """统一写权限检查，返回 (resolved_absolute_path, error)。

    三层检查：
    L1 - 路径合法性：复用 path_util.resolve_relative_path（不可读则不可写）
    L2 - 写黑名单：支持单段与多段路径模式
    L3 - 存在性：根据 must_exist 检查文件是否存在
    """
    # L1: 复用路径校验（拒绝空路径、绝对路径）
    relative_path, l1_error = _path_util.resolve_relative_path(file_path)
    if l1_error is not None:
        return None, l1_error

    # L2: 写黑名单 — 支持单段与多段路径模式
    no_write_patterns: list[str] = getattr(
        agent_client.config, "no_write_files", []
    )
    if _path_util.is_ignored_relative_path(relative_path, no_write_patterns):
        return None, f"错误：你无权修改这些文件：{', '.join(no_write_patterns)}"

    # L3: 存在性检查
    full_path = (pathlib.Path.cwd() / relative_path).resolve()
    if must_exist:
        if not full_path.is_file():
            return None, f"错误：文件不存在：{relative_path}"
    else:
        if full_path.exists():
            return None, f"错误：文件已存在：{relative_path}"

    return full_path, None


def create_file(
    agent_client: typing.Any,
    file_path: str,
    content: str | None = None,
) -> str:
    """创建新文件，不覆盖已有文件。

    @param file_path: 目标文件路径（相对工作目录，不接受绝对路径）
    @param content: 文件初始内容，缺省创建空文件
    """
    full_path, error = _resolve_writable_file(agent_client, file_path, must_exist=False)
    if error is not None:
        return error

    try:
        full_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exception:
        return f"错误：无法创建目录：{exception}"

    try:
        file_content = content if content is not None else ""
        full_path.write_text(file_content, encoding="utf-8", newline="")
    except OSError as exception:
        return f"错误：无法写入文件：{exception}"

    return "成功"


def delete_file(
    agent_client: typing.Any,
    file_path: str,
) -> str:
    """删除文件。

    @param file_path: 目标文件路径（相对工作目录，不接受绝对路径）
    """
    full_path, error = _resolve_writable_file(agent_client, file_path, must_exist=True)
    if error is not None:
        return error

    try:
        full_path.unlink()
    except OSError as exception:
        return f"错误：无法删除文件：{exception}"

    return "成功"


def apply_patch(
    agent_client: typing.Any,
    file_path: str,
    old_text: str,
    new_text: str | None = None,
) -> str:
    """替换文本。

    @param file_path: 目标文件路径（相对工作目录，不接受绝对路径）
    @param old_text: 要被替换的原文片段，须在文件中出现且仅出现一次
    @param new_text: 替换后的内容，缺省为空字符串
    """
    full_path, error = _resolve_writable_file(agent_client, file_path, must_exist=True)
    if error is not None:
        return error

    if not old_text:
        return "错误：old_text 不能为空字符串。"

    replacement = new_text if new_text is not None else ""
    updated, patch_error = _patch_file_content(full_path, old_text, replacement)
    if patch_error is not None:
        return patch_error

    try:
        full_path.write_text(updated, encoding="utf-8", newline="")
    except OSError as exception:
        return f"错误：无法写入文件：{exception}"
    return "成功"


def _patch_file_content(
    full_path: pathlib.Path,
    old_text: str,
    replacement: str,
) -> tuple[str | None, str | None]:
    try:
        content = full_path.read_text(encoding="utf-8")
    except OSError as exception:
        return None, f"错误：无法读取文件：{exception}"

    file_originally_had_crlf = "\r\n" in content
    work_content = _to_lf_for_patch_matching(content)
    work_old = _to_lf_for_patch_matching(old_text)
    work_replacement = _to_lf_for_patch_matching(replacement)

    occurrences = work_content.count(work_old)
    if occurrences == 0:
        return None, "错误：文件中未找到与 old_text 完全一致的片段。"
    if occurrences > 1:
        count_message = f"错误：old_text 在文件中出现 {occurrences} 次，必须为恰好 1 次。"
        return None, count_message

    index = work_content.index(work_old)
    updated_lf = (
        work_content[:index]
        + work_replacement
        + work_content[index + len(work_old):]
    )
    if file_originally_had_crlf:
        updated = updated_lf.replace("\n", "\r\n")
    else:
        updated = updated_lf
    return updated, None


def _to_lf_for_patch_matching(value: str) -> str:
    return value.replace("\r\n", "\n")
