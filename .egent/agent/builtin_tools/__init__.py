"""Agent 内置工具模块入口。"""

import importlib

__file_edit_tool = importlib.import_module(".file_edit_tool", __name__)
__grep_search_tool = importlib.import_module(".grep_search_tool", __name__)
__launch_game_tool = importlib.import_module(".launch_game_tool", __name__)
__memory_tool = importlib.import_module(".memory_tool", __name__)
__read_file_tool = importlib.import_module(".read_file_tool", __name__)
__shell_tool = importlib.import_module(".shell_tool", __name__)
__skill_tool = importlib.import_module(".skill_tool", __name__)
__system_info_tool = importlib.import_module(".system_info_tool", __name__)
__fuck_tool = importlib.import_module(".fuck_tool", __name__)
__walk_files_tool = importlib.import_module(".walk_files_tool", __name__)

__all__ = [
    "file_edit_tool",
    "grep_search_tool",
    "launch_game_tool",
    "memory_tool",
    "read_file_tool",
    "shell_tool",
    "skill_tool",
    "system_info_tool",
    "fuck_tool",
    "walk_files_tool",
]
