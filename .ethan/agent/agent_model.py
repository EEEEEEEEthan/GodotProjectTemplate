"""LLM 连接参数：API key、模型名与 base URL。"""

import dataclasses


@dataclasses.dataclass
class AgentModel:
    """LLM 连接参数。"""

    api_key: str | None = None
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
