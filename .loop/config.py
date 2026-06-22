"""流水线配置。"""

import tomllib
from pathlib import Path
from typing import Mapping

LOOP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = LOOP_ROOT.parent
SETTINGS_DIR = LOOP_ROOT / "settings"
BRIDGE_STATE_ROOT = LOOP_ROOT / ".bridge-state"
LOOP_SETTINGS_FILE = SETTINGS_DIR / "loop.toml"

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
