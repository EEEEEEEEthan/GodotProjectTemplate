"""从 .ethan 目录加载 model.toml、config.toml。"""

from __future__ import annotations

import json
import os
import pathlib
import tomllib

import agent.agent_config
import agent.agent_tools
import agent.mcp_bridge

ETHAN_ROOT = pathlib.Path.cwd() / ".ethan"
AGENTS_ROOT = ETHAN_ROOT / "agents"
GLOBAL_ETHAN_ROOT = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Ethan"
GLOBAL_MODEL_FILE = GLOBAL_ETHAN_ROOT / "model.toml"
GLOBAL_CONFIG_FILE = GLOBAL_ETHAN_ROOT / "config.toml"
DEFAULT_MODEL_FILE = ETHAN_ROOT / "model.toml"
DEFAULT_CONFIG_FILE = ETHAN_ROOT / "config.toml"
GLOBAL_MCP_FILE = GLOBAL_ETHAN_ROOT / "mcp.json"
DEFAULT_MCP_FILE = ETHAN_ROOT / "mcp.json"

DEFAULT_MCP: dict[str, dict[str, object]] = {
    "mcpServers": {
        "godot-game": {
            "command": "python",
            "args": [".ethan/mcp/server.py"],
        },
    },
}

DEFAULT_MODEL: dict[str, str] = {
    "model": "gpt-4o-mini",
    "baseUrl": "https://api.openai.com/v1",
}
DEFAULT_CONFIG: dict[str, str | list[str]] = {
    "systemPrompt": agent.agent_config.DEFAULT_SYSTEM_PROMPT,
    "skills": list(agent.agent_config.DEFAULT_SKILLS),
    "tools": list(agent.agent_tools.TOOL_SCHEMAS),
}


def load_model_toml(agent_name: str) -> dict:
    """加载合并后的 model.toml（global → project → agent）。"""
    agent_directory = __resolve_agent_directory(agent_name)
    return __load_merged_toml(
        GLOBAL_MODEL_FILE,
        DEFAULT_MODEL_FILE,
        agent_directory / "model.toml",
        DEFAULT_MODEL,
        header="模型与 API 连接配置",
        footer_lines=['# apiKey = "sk-..."'],
    )


def load_config_toml(agent_name: str) -> dict:
    """加载合并后的 config.toml（global → project → agent）。"""
    agent_directory = __resolve_agent_directory(agent_name)
    return __load_merged_toml(
        GLOBAL_CONFIG_FILE,
        DEFAULT_CONFIG_FILE,
        agent_directory / "config.toml",
        DEFAULT_CONFIG,
        header="Agent 行为配置",
    )


def load_mcp_servers() -> dict[str, agent.mcp_bridge.McpServerConfig]:
    """加载合并后的 mcp.json（global → project）。"""
    merged = __load_merged_json(
        GLOBAL_MCP_FILE,
        DEFAULT_MCP_FILE,
        DEFAULT_MCP,
    )
    return agent.mcp_bridge.parse_mcp_servers(merged)


def __resolve_agent_directory(agent_name: str) -> pathlib.Path:
    if not agent_name or not agent_name.strip():
        raise ValueError("agent_name 不能为空")
    agent_directory = AGENTS_ROOT / agent_name.strip()
    if not agent_directory.is_dir():
        raise FileNotFoundError(f"Agent 目录不存在：{agent_directory}")
    return agent_directory


def __load_toml_object(filepath: pathlib.Path) -> dict:
    data = tomllib.loads(filepath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式无效：{filepath}")
    return data


def __load_json_object(filepath: pathlib.Path) -> dict:
    data = json.loads(filepath.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式无效：{filepath}")
    return data


def __merge_mcp_layers(*layers: dict | None) -> dict:
    merged_servers: dict[str, object] = {}
    for layer in layers:
        if layer is None:
            continue
        raw_servers = layer.get("mcpServers")
        if isinstance(raw_servers, dict):
            merged_servers.update(raw_servers)
    return {"mcpServers": merged_servers}


def __load_merged_json(
    global_filepath: pathlib.Path,
    project_filepath: pathlib.Path,
    default_value: dict,
) -> dict:
    global_json = (
        __load_json_object(global_filepath) if global_filepath.is_file() else None
    )
    project_json = (
        __load_json_object(project_filepath) if project_filepath.is_file() else None
    )
    if global_json is None and project_json is None:
        __write_json_object(project_filepath, default_value)
        project_json = __load_json_object(project_filepath)
    return __merge_mcp_layers(global_json, project_json)


def __load_merged_toml(
    global_filepath: pathlib.Path,
    project_filepath: pathlib.Path,
    agent_filepath: pathlib.Path,
    default_value: dict,
    *,
    header: str | None = None,
    footer_lines: list[str] | None = None,
) -> dict:
    global_toml = (
        __load_toml_object(global_filepath) if global_filepath.is_file() else None
    )
    project_toml = (
        __load_toml_object(project_filepath) if project_filepath.is_file() else None
    )
    agent_toml = (
        __load_toml_object(agent_filepath) if agent_filepath.is_file() else None
    )
    if global_toml is None and project_toml is None and agent_toml is None:
        __write_toml_object(
            global_filepath,
            default_value,
            header=header,
            footer_lines=footer_lines,
        )
        global_toml = __load_toml_object(global_filepath)
    merged: dict = {}
    for layer in (global_toml, project_toml, agent_toml):
        if layer is not None:
            merged.update(layer)
    return merged


def __format_toml_string(value: str) -> str:
    if "\n" in value:
        escaped = value.replace("\\", "\\\\")
        return f'"""\n{escaped}\n"""'
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def __format_toml_value(value: object) -> str:
    if isinstance(value, str):
        return __format_toml_string(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        item_lines = [f"  {__format_toml_string(item)}," for item in value]
        return "[\n" + "\n".join(item_lines) + "\n]"
    raise TypeError(f"不支持的 TOML 值类型：{type(value)!r}")


def __format_toml_document(
    data: dict,
    *,
    header: str | None = None,
    footer_lines: list[str] | None = None,
) -> str:
    lines: list[str] = []
    if header:
        lines.append(f"# {header}")
        lines.append("")
    for key, value in data.items():
        lines.append(f"{key} = {__format_toml_value(value)}")
    if footer_lines:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(footer_lines)
    return "\n".join(lines) + "\n"


def __write_toml_object(
    filepath: pathlib.Path,
    data: dict,
    *,
    header: str | None = None,
    footer_lines: list[str] | None = None,
) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        __format_toml_document(data, header=header, footer_lines=footer_lines),
        encoding="utf-8",
    )


def __write_json_object(filepath: pathlib.Path, data: dict) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
