"""LLM 连接参数：从 model.toml 或环境变量加载。"""

from __future__ import annotations

import dataclasses
import os
import pathlib
import tomllib

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclasses.dataclass
class ModelConfig:
    """LLM 连接参数。"""

    api_key: str | None = None
    model: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    instructions: str | None = None

    def resolve_api_key(self) -> str:
        resolved_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_key:
            raise ValueError(
                "未设置 api_key，请在 model.toml 或环境变量 OPENAI_API_KEY 中配置",
            )
        return resolved_key

    @classmethod
    def load(cls, path: pathlib.Path | None = None) -> ModelConfig:
        if path is None:
            path = pathlib.Path(__file__).resolve().parent.parent / "model.toml"
        if not path.is_file():
            raise FileNotFoundError(f"找不到模型配置: {path}")
        with path.open("rb") as config_file:
            data = tomllib.load(config_file)
        return cls(
            api_key=data.get("api_key"),
            model=data.get("model", DEFAULT_MODEL),
            base_url=data.get("base_url", DEFAULT_BASE_URL),
            instructions=data.get("instructions"),
        )
