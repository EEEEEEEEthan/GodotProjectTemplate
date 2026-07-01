"""单 agent 多轮对话：基于 openai-agents Runner。"""

from __future__ import annotations

from agents import Agent, Runner, Session

from .model_runtime import ModelRuntime


class Conversation:
    """维护与单个 Agent 的多轮对话。"""

    def __init__(
        self,
        agent: Agent,
        model_runtime: ModelRuntime,
        *,
        session: Session | None = None,
    ) -> None:
        self._agent = agent
        self._model_runtime = model_runtime
        self._session = session

    @property
    def agent(self) -> Agent:
        return self._agent

    @property
    def session(self) -> Session | None:
        return self._session

    async def send(self, message: str, *, max_turns: int | None = None) -> str:
        run_kwargs: dict[str, object] = {
            "run_config": self._model_runtime.run_config,
            "session": self._session,
        }
        if max_turns is not None:
            run_kwargs["max_turns"] = max_turns
        result = await Runner.run(self._agent, message, **run_kwargs)
        return result.final_output or ""
