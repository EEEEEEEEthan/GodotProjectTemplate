"""Skill 索引：扫描 SKILL.md 并解析 front matter 元数据。"""

from __future__ import annotations

import pathlib


class SkillIndex:
    """扫描 skill 目录并维护 id 到路径/描述的索引。"""

    def __init__(self, paths: list[str]) -> None:
        ordered_entries: list[tuple[str, str, str]] = []

        for skill_directory in paths:
            if not skill_directory or not skill_directory.strip():
                continue
            skill_path = pathlib.Path(skill_directory.strip()).resolve()
            skill_markdown = skill_path / "SKILL.md"
            if not skill_markdown.is_file():
                continue

            parsed_name, parsed_description = self.__parse_frontmatter(skill_markdown)
            if parsed_name:
                base_name = parsed_name.strip()
                description = parsed_description.strip()
            else:
                base_name = skill_path.name
                description = parsed_description.strip()

            ordered_entries.append((str(skill_path), base_name, description))

        per_name_count: dict[str, int] = {}
        self.__entries: dict[str, tuple[str, str, str]] = {}

        for skill_directory, base_name, description in ordered_entries:
            occurrence = per_name_count.get(base_name, 0) + 1
            per_name_count[base_name] = occurrence
            identifier = base_name if occurrence == 1 else f"{base_name}{occurrence}"
            folder_name = pathlib.Path(skill_directory).name
            disambiguator = 0
            while identifier in self.__entries:
                disambiguator += 1
                identifier = (
                    f"{base_name}{occurrence}__{folder_name}"
                    if disambiguator == 1
                    else f"{base_name}{occurrence}__{folder_name}_{disambiguator}"
                )
            self.__entries[identifier] = (identifier, description, skill_directory)

    def get(self, skill_id: str) -> tuple[str, str, str] | None:
        """按 id 返回 (id, description, skill_root) 或 None。"""
        return self.__entries.get(skill_id)

    @property
    def prompt(self) -> str:
        """生成注入系统提示词的可用 skill 列表。"""
        lines = [
            "你可以根据需要使用技能.可用技能如下(- id: description):",
        ]
        for skill_id in sorted(self.__entries, key=str.casefold):
            _, description, _ = self.__entries[skill_id]
            lines.append(f"- {skill_id}: {description}")
        lines.append("")
        lines.append(
            "技能内可能包含脚本.先使用learn_skill工具查看技能的详细信息，再使用run_skill_script工具调用技能脚本."
        )
        return "\n".join(lines)

    @staticmethod
    def __parse_frontmatter(skill_markdown: pathlib.Path) -> tuple[str, str]:
        try:
            lines = skill_markdown.read_text(encoding="utf-8").splitlines()
        except OSError:
            return "", ""

        if not lines or lines[0].strip() != "---":
            return "", ""

        name = ""
        description = ""
        for line in lines[1:]:
            if line.strip() == "---":
                break
            colon_index = line.find(":")
            if colon_index <= 0:
                continue
            key = line[:colon_index].strip()
            value = line[colon_index + 1 :].strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            if key.lower() == "name":
                name = value
            elif key.lower() == "description":
                description = value

        return name, description
