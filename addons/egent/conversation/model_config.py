"""LLM 连接参数：从 .model.toml 按配置节与档位加载。"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import tomllib

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_CONFIG_PATH = pathlib.Path(__file__).resolve().parent.parent / ".model.toml"
RESERVED_PROFILE_KEYS = frozenset({"key", "url"})

MODEL_CONFIG_TEMPLATE = """\
[coconut]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"

[openai]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"

[vocal]
key = "OPENAI_KEY"
url = "OPENAI_URL"
high = "MODEL_NAME"
low = "MODEL_NAME"
"""


class ConfigTemplateCreatedError(FileNotFoundError):
    """配置文件已自动创建，需用户填写后重试。"""


@dataclasses.dataclass
class ModelConfig:
    """LLM 连接参数。"""

    api_key: str | None
    base_url: str
    model: str
    profile_name: str
    tier_name: str
    instructions: str | None = None

    def resolve_api_key(self) -> str:
        resolved_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                f"配置节 [{self.profile_name}] 未设置 key，"
                f"请在 .model.toml 或环境变量 OPENAI_API_KEY 中配置",
            )
        return resolved_key

    @classmethod
    def load(
        cls,
        profile_name: str,
        tier_name: str,
        path: pathlib.Path | None = None,
    ) -> ModelConfig:
        config_path = path or DEFAULT_CONFIG_PATH
        ensure_model_config_file(config_path)
        with config_path.open("rb") as config_file:
            profiles = tomllib.load(config_file)
        profile = profiles.get(profile_name)
        if not isinstance(profile, dict):
            available_profiles = [
                name
                for name, data in profiles.items()
                if isinstance(data, dict)
            ]
            raise ValueError(
                f"未知配置节 {profile_name!r}，可选: {available_profiles}",
            )
        tier_names = [
            field_name
            for field_name in profile
            if field_name not in RESERVED_PROFILE_KEYS
        ]
        if tier_name not in tier_names:
            raise ValueError(
                f"配置节 [{profile_name}] 不存在档位 {tier_name!r}，"
                f"可选: {tier_names}",
            )
        model_name = profile[tier_name]
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError(
                f"配置节 [{profile_name}] 档位 {tier_name!r} 的模型名为空",
            )
        base_url = profile.get("url", DEFAULT_BASE_URL)
        if not isinstance(base_url, str) or not base_url.strip():
            base_url = DEFAULT_BASE_URL
        api_key = profile.get("key")
        if api_key is not None and not isinstance(api_key, str):
            api_key = None
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model_name.strip(),
            profile_name=profile_name,
            tier_name=tier_name,
        )


def ensure_model_config_file(path: pathlib.Path) -> None:
    if path.is_file():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(MODEL_CONFIG_TEMPLATE, encoding="utf-8")
    raise ConfigTemplateCreatedError(
        f"已创建配置模板 {path}，请填写后重新运行",
    )

