"""流水线配置。"""

import os
import sys
import tomllib
from pathlib import Path
from typing import Mapping

LOOP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = LOOP_ROOT.parent
SETTINGS_DIR = LOOP_ROOT / "settings"
BRIDGE_STATE_ROOT = LOOP_ROOT / ".bridge-state"
LOOP_SETTINGS_FILE = SETTINGS_DIR / "loop.toml"
PROJECT_ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_MODEL = "composer-2.5"
BRIDGE_LAUNCH_TIMEOUT_SECONDS = 60.0
MAX_EXECUTOR_ROUNDS = 15
MAX_REVIEW_CYCLES = 5
MAX_REDO_CYCLES = 3

ROLE_KEYS = ("lead", "executor")
VALID_SETTING_SOURCES = frozenset(
    {"project", "user", "team", "mdm", "plugins", "all"}
)
DEFAULT_SETTING_SOURCES: list[str] = ["all"]


def _parse_setting_sources_value(
    raw_value: object,
    *,
    context: str,
) -> list[str]:
    if raw_value is None:
        return list(DEFAULT_SETTING_SOURCES)
    if isinstance(raw_value, str):
        sources = [raw_value]
    elif isinstance(raw_value, list):
        sources = [str(item) for item in raw_value]
    else:
        raise ValueError(f"{context} 中 setting_sources 必须是字符串或字符串列表")

    if not sources:
        return []

    unknown = [source for source in sources if source not in VALID_SETTING_SOURCES]
    if unknown:
        allowed = ", ".join(sorted(VALID_SETTING_SOURCES))
        raise ValueError(f"{context} 含未知 setting_sources: {unknown}；可选: {allowed}")

    if "all" in sources and len(sources) > 1:
        raise ValueError(f"{context} 中 setting_sources 含 all 时不应再列其他项")

    return sources


def _load_loop_settings() -> dict:
    if not LOOP_SETTINGS_FILE.is_file():
        return {}
    with LOOP_SETTINGS_FILE.open("rb") as settings_file:
        return tomllib.load(settings_file)


def load_role_setting_sources(role: str) -> list[str]:
    if role not in ROLE_KEYS:
        allowed_roles = ", ".join(ROLE_KEYS)
        raise ValueError(f"未知角色 {role!r}；可选: {allowed_roles}")

    parsed = _load_loop_settings()
    role_section = parsed.get(role)
    if not isinstance(role_section, dict):
        return list(DEFAULT_SETTING_SOURCES)

    return _parse_setting_sources_value(
        role_section.get("setting_sources", DEFAULT_SETTING_SOURCES),
        context=f"{LOOP_SETTINGS_FILE} [{role}]",
    )


def load_all_role_setting_sources() -> dict[str, list[str]]:
    return {role: load_role_setting_sources(role) for role in ROLE_KEYS}


def union_bridge_setting_sources(
    sources_by_role: Mapping[str, list[str]],
) -> list[str]:
    if any("all" in sources for sources in sources_by_role.values()):
        return ["all"]

    merged: list[str] = []
    for sources in sources_by_role.values():
        for source in sources:
            if source not in merged:
                merged.append(source)
    return merged


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    if stripped.startswith("export "):
        stripped = stripped[7:].strip()
    if "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    if not key:
        return None
    return key, value


def load_project_dotenv(path: Path = PROJECT_ENV_FILE) -> dict[str, str]:
    if not path.is_file():
        return {}
    variables: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_dotenv_line(line)
        if parsed is not None:
            variables[parsed[0]] = parsed[1]
    return variables


def load_cursor_api_key() -> str | None:
    environment_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if environment_key:
        return environment_key
    file_key = load_project_dotenv().get("CURSOR_API_KEY", "").strip()
    if file_key:
        return file_key
    return None


def ensure_cursor_api_key_env() -> str:
    api_key = load_cursor_api_key()
    if not api_key:
        print(
            "请设置环境变量 CURSOR_API_KEY，或在 "
            f"{PROJECT_ENV_FILE} 中配置 CURSOR_API_KEY=...",
            file=sys.stderr,
        )
        sys.exit(1)
    if not os.environ.get("CURSOR_API_KEY"):
        os.environ["CURSOR_API_KEY"] = api_key
    return api_key
