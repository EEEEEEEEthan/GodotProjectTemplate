"""openai-agents 运行配置：模型端点与 RunConfig。"""

from __future__ import annotations

import dataclasses

from agents import RunConfig, set_default_openai_api, set_default_openai_client
from agents.models.openai_provider import OpenAIProvider
from openai import AsyncOpenAI

from .model_config import ModelConfig


@dataclasses.dataclass
class ModelRuntime:
    """封装 Agents SDK 的模型提供方与单次运行配置。"""

    config: ModelConfig
    run_config: RunConfig

    @classmethod
    def from_config(cls, config: ModelConfig) -> ModelRuntime:
        client = AsyncOpenAI(
            api_key=config.resolve_api_key(),
            base_url=config.base_url,
        )
        set_default_openai_client(client)
        set_default_openai_api("chat_completions")
        provider = OpenAIProvider(
            openai_client=client,
            use_responses=False,
        )
        run_config = RunConfig(model=config.model, model_provider=provider)
        return cls(config=config, run_config=run_config)
