"""文件编辑工具：创建文件与应用 unified diff 补丁。"""

from __future__ import annotations

import pathlib


class FileEditTool:
    """Agent 文件创建与文本替换工具。"""

    @staticmethod
    def create_file(
        file_path: str,
        content: str | None = None,
    ) -> str:
        """创建新文件，不覆盖已有文件。

        @param file_path: 目标文件路径（相对工作目录，不接受绝对路径）
        @param content: 文件初始内容，缺省创建空文件
        """
        if not file_path or not file_path.strip():
            return "错误：file_path 不能为空。"

        relative_path = pathlib.Path(file_path.strip())
        if relative_path.is_absolute():
            return f"错误：file_path 必须是相对工作目录的路径，不接受绝对路径：{file_path}"

        full_path = (pathlib.Path.cwd() / relative_path).resolve()
        if full_path.exists():
            return f"错误：文件已存在：{relative_path}"

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

    @staticmethod
    def apply_patch(
        file_path: str,
        old_text: str,
        new_text: str | None = None,
    ) -> str:
        """替换文本。

        @param file_path: 目标文件路径，可为绝对路径或相对当前工作目录
        @param old_text: 要被替换的原文片段，须在文件中出现且仅出现一次
        @param new_text: 替换后的内容，缺省为空字符串
        """
        validation_error = FileEditTool.__validate_patch_input(file_path, old_text)
        if validation_error is not None:
            return validation_error

        full_path, resolve_error = FileEditTool.__resolve_patch_target(file_path)
        if resolve_error is not None:
            return resolve_error

        replacement = new_text if new_text is not None else ""
        updated, patch_error = FileEditTool.__patch_file_content(
            full_path,
            old_text,
            replacement,
        )
        if patch_error is not None:
            return patch_error

        try:
            full_path.write_text(updated, encoding="utf-8", newline="")
        except OSError as exception:
            return f"错误：无法写入文件：{exception}"
        return "成功"

    @staticmethod
    def __validate_patch_input(file_path: str, old_text: str) -> str | None:
        if not file_path or not file_path.strip():
            return "错误：file_path 不能为空。"
        if not old_text:
            return "错误：old_text 不能为空字符串。"
        return None

    @staticmethod
    def __resolve_patch_target(
        file_path: str,
    ) -> tuple[pathlib.Path | None, str | None]:
        try:
            full_path = pathlib.Path(file_path.strip()).resolve()
        except OSError as exception:
            return None, f"错误：路径无效：{exception}"
        if not full_path.is_file():
            return None, f"错误：文件不存在：{full_path}"
        return full_path, None

    @staticmethod
    def __patch_file_content(
        full_path: pathlib.Path,
        old_text: str,
        replacement: str,
    ) -> tuple[str | None, str | None]:
        try:
            content = full_path.read_text(encoding="utf-8")
        except OSError as exception:
            return None, f"错误：无法读取文件：{exception}"

        file_originally_had_crlf = "\r\n" in content
        work_content = FileEditTool.__to_lf_for_patch_matching(content)
        work_old = FileEditTool.__to_lf_for_patch_matching(old_text)
        work_replacement = FileEditTool.__to_lf_for_patch_matching(replacement)

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
            + work_content[index + len(work_old) :]
        )
        if file_originally_had_crlf:
            updated = updated_lf.replace("\n", "\r\n")
        else:
            updated = updated_lf
        return updated, None

    @staticmethod
    def __to_lf_for_patch_matching(value: str) -> str:
        return value.replace("\r\n", "\n")
