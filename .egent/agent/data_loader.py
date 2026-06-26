"""从 .egent 目录加载 model.toml（API Key）与 mcp.json。"""

from __future__ import annotations

import json
import os
import pathlib
import tomllib

import agent_config
import agent.mcp_bridge

_PACKAGE_DIR = pathlib.Path(__file__).resolve().parent
EGENT_ROOT = _PACKAGE_DIR.parent
PROJECT_ROOT = EGENT_ROOT.parent
EGENT_TEMP_DIR = EGENT_ROOT / ".temp"
AGENTS_ROOT = EGENT_ROOT / "agents"
GLOBAL_EGENT_ROOT = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Egent"
GLOBAL_MODEL_KEYS_FILE = GLOBAL_EGENT_ROOT / "model.toml"
DEFAULT_MODEL_KEYS_FILE = EGENT_ROOT / "model.toml"
GLOBAL_MCP_FILE = GLOBAL_EGENT_ROOT / "mcp.json"
DEFAULT_MCP_FILE = EGENT_ROOT / "mcp.json"

DEFAULT_MCP: dict[str, dict[str, object]] = {
    "mcpServers": {
        "godot-game": {
            "command": "python",
            "args": ["-m", "godot_mcp.server"],
            "cwd": ".egent",
        },
    },
}


def load_api_keys() -> dict[str, str]:
    """加载 model.toml 中的 API Key 键值对（global → project，后者覆盖）。"""
    __ensure_model_keys_file()
    merged: dict[str, str] = {}
    for filepath in (GLOBAL_MODEL_KEYS_FILE, DEFAULT_MODEL_KEYS_FILE):
        if not filepath.is_file():
            continue
        data = __load_toml_object(filepath)
        for key, value in data.items():
            if isinstance(key, str) and isinstance(value, str):
                merged[key] = value
    return merged


def __ensure_model_keys_file() -> None:
    """若项目 model.toml 不存在则按 agent_config 自动生成。"""
    if DEFAULT_MODEL_KEYS_FILE.is_file():
        return
    required_keys = {
        definition.key for definition in agent_config.AGENTS.values()
    }
    __write_toml_object(
        DEFAULT_MODEL_KEYS_FILE,
        {key: "" for key in sorted(required_keys)},
        header="API Key 键值对；由程序自动生成，请填写真实 key",
    )


def load_mcp_servers() -> dict[str, agent.mcp_bridge.McpServerConfig]:
    """加载合并后的 mcp.json（global → project）。"""
    merged = __load_merged_json(
        GLOBAL_MCP_FILE,
        DEFAULT_MCP_FILE,
        DEFAULT_MCP,
    )
    return agent.mcp_bridge.parse_mcp_servers(merged)


def resolve_agent_directory(agent_name: str) -> pathlib.Path:
    """解析并校验 agents/<name> 目录。"""
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


def __write_json_object(filepath: pathlib.Path, data: dict) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def __format_toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def __format_toml_document(
    data: dict[str, str],
    *,
    header: str | None = None,
) -> str:
    lines: list[str] = []
    if header:
        lines.append(f"# {header}")
        lines.append("")
    for key, value in data.items():
        lines.append(f"{key} = {__format_toml_string(value)}")
    return "\n".join(lines) + "\n"


def __write_toml_object(
    filepath: pathlib.Path,
    data: dict[str, str],
    *,
    header: str | None = None,
) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(
        __format_toml_document(data, header=header),
        encoding="utf-8",
    )
