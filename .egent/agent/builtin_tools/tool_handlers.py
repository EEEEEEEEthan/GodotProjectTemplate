"""业务层工具集构建：按场景组装 Agent 可调用的工具方法列表。"""

from __future__ import annotations

import typing

import agent.tool_binding
import agent.builtin_tools.file_edit_tool as file_edit_tool
import agent.builtin_tools.fuck_tool as fuck_tool
import agent.builtin_tools.grep_search_tool as grep_search_tool
import agent.builtin_tools.launch_game_tool as launch_game_tool
import agent.builtin_tools.memory_tool as memory_tool
import agent.builtin_tools.read_file_tool as read_file_tool
import agent.builtin_tools.shell_tool as shell_tool
import agent.builtin_tools.skill_tool as skill_tool
import agent.builtin_tools.system_info_tool as system_info_tool
import agent.builtin_tools.walk_files_tool as walk_files_tool

if typing.TYPE_CHECKING:
    import agent.agent_client


def get_all_tools(
    agent_client: agent.agent_client.AgentClient,
) -> list[agent.tool_binding.ToolHandler]:
    """返回全量工具集。"""
    return agent.tool_binding.wrap_tools(
        agent_client,
        skill_tool.learn_skill,
        skill_tool.run_skill_script,
        file_edit_tool.create_file,
        file_edit_tool.apply_patch,
        grep_search_tool.grep_search,
        shell_tool.exec,
        shell_tool.bg_exec,
        shell_tool.bg_status,
        shell_tool.wait,
        walk_files_tool.walk_files,
        system_info_tool.system_info,
        fuck_tool.fuck,
        memory_tool.add_item,
        memory_tool.remove_item,
        memory_tool.update_item,
        memory_tool.list_items,
        memory_tool.find_str,
        read_file_tool.read_file_outline_cs,
        read_file_tool.read_file_outline_md,
        read_file_tool.read_file_outline_py,
        read_file_tool.read_lines,
        read_file_tool.read_whole_file,
        launch_game_tool.launch_game,
    )
