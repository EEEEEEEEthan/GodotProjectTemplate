"""从 .model.json 加载模型连接配置。"""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass

DEFAULT_CONFIG_PATH = pathlib.Path(__file__).resolve().parent / ".model.json"

DEFAULT_PROFILES = {
    "coconut": {
        "key": "OPENAI_KEY",
        "url": "OPENAI_URL",
        "models": {"high": "MODEL_NAME", "low": "MODEL_NAME"},
    },
    "openai": {
        "key": "OPENAI_KEY",
        "url": "OPENAI_URL",
        "models": {"high": "MODEL_NAME", "low": "MODEL_NAME"},
    },
    "vocal": {
        "key": "OPENAI_KEY",
        "url": "OPENAI_URL",
        "models": {"high": "MODEL_NAME", "low": "MODEL_NAME"},
    },
}


class ConfigTemplateCreatedError(FileNotFoundError):
    """配置文件已自动创建，需用户填写后重试。"""


@dataclass
class ModelSettings:
    """指定 profile 与 model 别名的 API 连接参数。"""

    api_key: str
    base_url: str
    model_name: str
    profile_name: str
    model_alias: str

    @staticmethod
    def load(profile_name: str, model_alias: str) -> ModelSettings:
        """读取配置；若文件不存在则创建模板并抛出 ConfigTemplateCreatedError。"""
        path = DEFAULT_CONFIG_PATH
        if not path.is_file():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(DEFAULT_PROFILES, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            raise ConfigTemplateCreatedError(
                f"已创建配置模板 {path}，请填写后重新运行",
            )
        try:
            profiles = json.loads(path.read_text(encoding="utf-8"))
            profile = profiles[profile_name]
            return ModelSettings(
                api_key=profile["key"] or os.getenv("OPENAI_API_KEY"),
                base_url=profile.get("url") or "https://api.openai.com/v1",
                model_name=profile["models"][model_alias],
                profile_name=profile_name,
                model_alias=model_alias,
            )
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            raise ValueError(
                f"配置无效: profile={profile_name!r} model={model_alias!r}",
            ) from error
