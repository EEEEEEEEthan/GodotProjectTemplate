"""Agent 内置工具模块入口。"""

import importlib

__file_edit_tool = importlib.import_module(".file_edit_tool", __name__)
__grep_search_tool = importlib.import_module(".grep_search_tool", __name__)
__memory_tool = importlib.import_module(".memory_tool", __name__)
__read_file_tool = importlib.import_module(".read_file_tool", __name__)
__skill_tool = importlib.import_module(".skill_tool", __name__)
__system_info_tool = importlib.import_module(".system_info_tool", __name__)
__walk_files_tool = importlib.import_module(".walk_files_tool", __name__)

FileEditTool = __file_edit_tool.FileEditTool
GrepSearchTool = __grep_search_tool.GrepSearchTool
MemoryTool = __memory_tool.MemoryTool
ReadFileTool = __read_file_tool.ReadFileTool
SkillTool = __skill_tool.SkillTool
SystemInfoTool = __system_info_tool.SystemInfoTool
WalkFilesTool = __walk_files_tool.WalkFilesTool

__all__ = [
    "FileEditTool",
    "GrepSearchTool",
    "MemoryTool",
    "ReadFileTool",
    "SkillTool",
    "SystemInfoTool",
    "WalkFilesTool",
]
