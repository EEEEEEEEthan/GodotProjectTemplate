"""Agent 客户端：加载配置、调用 LLM 并流式产出事件。"""

from __future__ import annotations

import asyncio
import collections.abc
import dataclasses
import typing

import httpx
import openai

import agent.agent_config
import agent.agent_events
import agent.agent_model
import agent.agent_tools
import agent.data_loader
import agent.log_manager
import agent.mcp_bridge
import agent.skill_index
import agent.tool_binding

if typing.TYPE_CHECKING:
    import wrapped_agent

MAX_INFLIGHT_CONTEXT_CHARS = 120_000
KEEP_RECENT_TOOL_MESSAGES = 8
MAX_STREAM_RETRIES = 3
_STREAM_RETRY_BACKOFF_SECONDS = 1.5
_TOOL_RESULT_OMITTED = "\n[较早的工具结果已省略以控制上下文大小]"
_STREAM_RETRYABLE_ERRORS = (
    httpx.RemoteProtocolError,
    httpx.ReadTimeout,
    httpx.ConnectError,
    httpx.WriteError,
    openai.APIConnectionError,
)
STREAM_RETRYABLE_ERRORS = _STREAM_RETRYABLE_ERRORS


@dataclasses.dataclass
class _ConversationState:
    history: list[dict[str, typing.Any]]
    openai_client: openai.AsyncOpenAI | None = None


@dataclasses.dataclass
class _AgentTooling:
    skill_index: agent.skill_index.SkillIndex
    system_prompt: str
    mcp_bridge: agent.mcp_bridge.McpBridge | None = None
    mcp_schemas: dict[str, dict[str, typing.Any]] = dataclasses.field(
        default_factory=dict,
    )
    mcp_ready: bool = False


class AgentClient:
    """封装 LLM 会话、工具调用与对话历史。"""

    @classmethod
    async def create(
        cls,
        name: str,
        model: agent.agent_model.AgentModel,
        config: agent.agent_config.AgentConfig,
    ) -> AgentClient:
        """构造 AgentClient 并完成 MCP 工具发现。"""
        client = cls(name, model, config)
        await client.__ensure_mcp_ready()
        return client

    @staticmethod
    async def load_agent(path: str) -> wrapped_agent.WrappedAgent:
        """从 agent_definition.py 加载 agent，API Key 从 model.toml 解析。"""
        import agent_definition

        return await agent_definition.get_definition(path).instantiate()

    def __init__(
        self,
        name: str,
        model: agent.agent_model.AgentModel,
        config: agent.agent_config.AgentConfig,
    ) -> None:
        if not name or not name.strip():
            raise ValueError("name 不能为空")
        if not config.system_prompt or not config.system_prompt.strip():
            raise ValueError("system_prompt 不能为空")

        self.name = name.strip()
        self.__model = model
        self.config = config
        self.skill_index = agent.skill_index.SkillIndex(config.skills)
        self.__conversation = self.__open_conversation()
        self.__tooling = self.__build_tooling(config)
        self.__mcp_ready_lock = asyncio.Lock()

        self.__conversation.history.append(
            {"role": "system", "content": self.__tooling.system_prompt}
        )

    def __open_conversation(self) -> _ConversationState:
        return _ConversationState(history=[])

    def __compose_system_prompt(self, base_prompt: str) -> str:
        parts: list[str] = []
        has_learn_skill = any(
            agent.tool_binding.resolve_tool_name(handler) == "skill_tool_learn_skill"
            for handler in self.config.default_tools
        )
        if has_learn_skill:
            parts.append(self.skill_index.prompt)
        parts.append(base_prompt)
        return "\n\n".join(
            part.strip()
            for part in parts
            if part.strip()
        )

    def __build_tooling(self, config: agent.agent_config.AgentConfig) -> _AgentTooling:
        return _AgentTooling(
            skill_index=self.skill_index,
            system_prompt=self.__compose_system_prompt(config.system_prompt),
        )

    async def __ensure_mcp_ready(self) -> None:
        tooling = self.__tooling
        if not self.config.mcp_servers or tooling.mcp_ready:
            return
        async with self.__mcp_ready_lock:
            if not self.config.mcp_servers or tooling.mcp_ready:
                return
            tooling.mcp_bridge = await agent.mcp_bridge.get_shared_bridge(
                self.config.mcp_servers,
            )
            tooling.mcp_schemas = tooling.mcp_bridge.all_schemas()
            tooling.mcp_ready = True

    def __resolve_send_handlers(
        self,
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None,
    ) -> tuple[agent.tool_binding.ToolHandler, ...]:
        if override_tools is not None:
            return override_tools
        return agent.tool_binding.wrap_tools(self, *self.config.default_tools)

    def __uses_default_tools(
        self,
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None,
    ) -> bool:
        return override_tools is None

    def __resolve_active_bindings(
        self,
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None,
    ) -> dict[str, agent.tool_binding.ToolBinding]:
        return agent.tool_binding.bind_tools(
            *self.__resolve_send_handlers(override_tools),
        )

    def __build_advertised_tools(
        self,
        active_bindings: dict[str, agent.tool_binding.ToolBinding],
        *,
        include_mcp: bool = True,
    ) -> list[dict[str, typing.Any]]:
        if not include_mcp:
            return agent.tool_binding.to_openai_tools(active_bindings)
        return agent.tool_binding.merge_advertised_tools(
            active_bindings,
            self.__tooling.mcp_schemas,
        )

    def __build_invoke(
        self,
        active_bindings: dict[str, agent.tool_binding.ToolBinding],
        *,
        include_mcp: bool = True,
    ) -> typing.Callable[[str, dict[str, typing.Any]], collections.abc.Awaitable[str]]:
        mcp_bridge = self.__tooling.mcp_bridge
        extra_schemas = self.__tooling.mcp_schemas if include_mcp else None

        async def invoke_mcp_tool(
            openai_name: str,
            arguments: dict[str, typing.Any],
        ) -> str:
            if mcp_bridge is None:
                return f"错误：MCP 未配置 {openai_name}"
            return await mcp_bridge.invoke(openai_name, arguments)

        return agent.agent_tools.build_tool_dispatch(
            active_bindings,
            extra_schemas=extra_schemas,
            mcp_invoke=invoke_mcp_tool if mcp_bridge is not None and include_mcp else None,
        )

    async def send(
        self,
        role: str,
        prompt: str,
        *,
        add_to_history: bool = True,
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None = None,
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        """发送单条消息并流式返回事件。"""
        async for event in self.send_messages(
            [{"role": role, "content": prompt}],
            add_to_history=add_to_history,
            override_tools=override_tools,
        ):
            yield event

    async def send_messages(
        self,
        contents: list[dict[str, typing.Any]],
        *,
        add_to_history: bool = True,
        override_tools: tuple[agent.tool_binding.ToolHandler, ...] | None = None,
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        """发送多条消息，可选写入历史与日志。"""
        await self.__ensure_mcp_ready()
        conversation = self.__conversation
        chat_history = list(conversation.history)
        chat_history.extend(contents)
        if add_to_history:
            conversation.history.extend(contents)
            for message in contents:
                role = message.get("role", "")
                content = message.get("content")
                if content:
                    agent.log_manager.write(f"[{role}]\n{content}\n\n")

        active_bindings = self.__resolve_active_bindings(override_tools)
        include_mcp = self.__uses_default_tools(override_tools)
        advertised_tools = self.__build_advertised_tools(
            active_bindings,
            include_mcp=include_mcp,
        )
        invoke = self.__build_invoke(
            active_bindings,
            include_mcp=include_mcp,
        )

        text_buffer: list[str] = []
        async for event in self.__run_turn(
            chat_history,
            text_buffer,
            advertised_tools,
            invoke,
        ):
            if add_to_history:
                if isinstance(event, agent.agent_events.TextDelta):
                    agent.log_manager.write(event.text)
                elif isinstance(event, agent.agent_events.ToolInvoking):
                    agent.log_manager.write("\n")
                    tool_header = (
                        f"[{event.name}]"
                        if not event.arguments
                        else (
                            f"[{event.name}] "
                            f"{agent.agent_tools.format_tool_arguments(event.arguments)}"
                        )
                    )
                    agent.log_manager.write(f"{tool_header}\n")
                elif isinstance(event, agent.agent_events.ToolInvoked):
                    if event.result:
                        agent.log_manager.write(f"{event.result}\n")
            yield event

        if add_to_history:
            reply = "".join(text_buffer)
            if reply and not (
                conversation.history
                and conversation.history[-1].get("role") == "assistant"
                and conversation.history[-1].get("content") == reply
            ):
                conversation.history.append({"role": "assistant", "content": reply})
            agent.log_manager.write("\n")
            agent.log_manager.flush()

    async def __run_turn(
        self,
        messages: list[dict[str, typing.Any]],
        text_buffer: list[str],
        advertised_tools: list[dict[str, typing.Any]],
        invoke: typing.Callable[
            [str, dict[str, typing.Any]],
            collections.abc.Awaitable[str],
        ],
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        client = self.__get_or_create_client()

        while True:
            AgentClient.__trim_inflight_context(messages, MAX_INFLIGHT_CONTEXT_CHARS)
            turn_text: list[str] = []
            tool_calls_by_index: dict[int, dict[str, typing.Any]] = {}
            buffer_checkpoint = len(text_buffer)

            for attempt in range(MAX_STREAM_RETRIES):
                turn_text.clear()
                tool_calls_by_index.clear()
                del text_buffer[buffer_checkpoint:]

                try:
                    stream = await client.chat.completions.create(
                        model=self.__model.model,
                        messages=messages,
                        tools=advertised_tools or None,
                        stream=True,
                    )

                    async for chunk in stream:
                        delta = chunk.choices[0].delta
                        if delta.content:
                            turn_text.append(delta.content)
                            text_buffer.append(delta.content)
                            yield agent.agent_events.TextDelta(delta.content)
                        if delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                AgentClient.__merge_tool_call_delta(
                                    tool_calls_by_index,
                                    tool_call,
                                )
                    break
                except _STREAM_RETRYABLE_ERRORS:
                    if attempt + 1 >= MAX_STREAM_RETRIES:
                        raise
                    await asyncio.sleep(_STREAM_RETRY_BACKOFF_SECONDS * (attempt + 1))

            full_text = "".join(turn_text)
            tool_calls = [
                tool_calls_by_index[index]
                for index in sorted(tool_calls_by_index)
            ]
            messages.append(
                AgentClient.__build_assistant_message(full_text, tool_calls)
            )

            if not tool_calls:
                yield agent.agent_events.TurnCompleted(full_text)
                return

            async for event in self.__invoke_tool_calls(
                tool_calls,
                messages,
                invoke,
            ):
                yield event

    async def __invoke_tool_calls(
        self,
        tool_calls: list[dict[str, typing.Any]],
        messages: list[dict[str, typing.Any]],
        invoke: typing.Callable[
            [str, dict[str, typing.Any]],
            collections.abc.Awaitable[str],
        ],
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        for tool_call in tool_calls:
            openai_name = tool_call["function"]["name"]
            arguments = agent.agent_tools.parse_tool_arguments(
                tool_call["function"]["arguments"],
            )
            tool_name = openai_name
            yield agent.agent_events.ToolInvoking(tool_name, arguments)
            result = await invoke(openai_name, arguments)
            yield agent.agent_events.ToolInvoked(
                tool_name,
                arguments,
                result,
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }
            )

    @staticmethod
    def __estimate_messages_chars(messages: list[dict[str, typing.Any]]) -> int:
        total = 0
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                total += len(content)
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    if isinstance(function, dict):
                        name = function.get("name")
                        arguments = function.get("arguments")
                        if isinstance(name, str):
                            total += len(name)
                        if isinstance(arguments, str):
                            total += len(arguments)
        return total

    @staticmethod
    def __trim_inflight_context(
        messages: list[dict[str, typing.Any]],
        max_chars: int,
    ) -> bool:
        """截断较早的 tool 结果以降低当轮 API 请求体大小。"""
        if AgentClient.__estimate_messages_chars(messages) <= max_chars:
            return False

        tool_indices = [
            index
            for index, message in enumerate(messages)
            if message.get("role") == "tool"
        ]
        protected = set(tool_indices[-KEEP_RECENT_TOOL_MESSAGES:])
        trimmed = False
        for index in tool_indices:
            if index in protected:
                continue
            content = messages[index].get("content")
            if isinstance(content, str) and content != _TOOL_RESULT_OMITTED:
                messages[index]["content"] = _TOOL_RESULT_OMITTED
                trimmed = True
                if AgentClient.__estimate_messages_chars(messages) <= max_chars:
                    return trimmed

        for index in tool_indices:
            if index not in protected:
                continue
            content = messages[index].get("content")
            if isinstance(content, str) and len(content) > len(_TOOL_RESULT_OMITTED):
                messages[index]["content"] = _TOOL_RESULT_OMITTED
                trimmed = True
                if AgentClient.__estimate_messages_chars(messages) <= max_chars:
                    return trimmed
        return trimmed

    @staticmethod
    def __merge_tool_call_delta(
        tool_calls_by_index: dict[int, dict[str, typing.Any]],
        tool_call,
    ) -> None:
        index = tool_call.index
        entry = tool_calls_by_index.setdefault(
            index,
            {
                "id": "",
                "type": "function",
                "function": {"name": "", "arguments": ""},
            },
        )
        if tool_call.id:
            entry["id"] = tool_call.id
        if tool_call.function and tool_call.function.name:
            entry["function"]["name"] = tool_call.function.name
        if tool_call.function and tool_call.function.arguments:
            entry["function"]["arguments"] += tool_call.function.arguments

    @staticmethod
    def __build_assistant_message(
        full_text: str,
        tool_calls: list[dict[str, typing.Any]],
    ) -> dict[str, typing.Any]:
        assistant_message: dict[str, typing.Any] = {
            "role": "assistant",
            "content": full_text or None,
        }
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        return assistant_message

    @property
    def tools(self) -> tuple[agent.tool_binding.ToolHandler, ...]:
        """当前 agent 默认工具方法（已注入 client）。"""
        return self.__resolve_send_handlers(None)

    @property
    def system_prompt(self) -> str:
        """合并 skill 提示后的完整系统提示词。"""
        return self.__tooling.system_prompt

    def __collect_tool_names(self) -> list[str]:
        tooling = self.__tooling
        bindings = self.__resolve_active_bindings(None)
        names = sorted(bindings)
        for openai_name in sorted(tooling.mcp_schemas):
            if openai_name not in bindings:
                names.append(openai_name)
        return names

    @property
    def tool_names(self) -> list[str]:
        """可用工具名（内置 + MCP）。"""
        return self.__collect_tool_names()

    @property
    def model(self) -> str:
        """LLM 模型名。"""
        return self.__model.model

    @property
    def base_url(self) -> str:
        """OpenAI 兼容 API 的 base URL。"""
        return self.__model.base_url.strip() or "https://api.openai.com/v1"

    async def aclose(self) -> None:
        """清理 MCP 状态（日志由 log_manager 的 atexit 自动关闭）。"""
        self.__tooling.mcp_ready = False
        self.__tooling.mcp_bridge = None

    def close(self) -> None:
        """日志由 log_manager 的 atexit 自动关闭，本方法仅保留兼容接口。"""

    def __get_or_create_client(self) -> openai.AsyncOpenAI:
        conversation = self.__conversation
        if conversation.openai_client is None:
            base_url = self.__model.base_url.strip() or "https://api.openai.com/v1"
            conversation.openai_client = openai.AsyncOpenAI(
                api_key=self.__model.api_key or "",
                base_url=base_url,
                timeout=300,
            )
        return conversation.openai_client

    async def __aenter__(self) -> AgentClient:
        await self.__ensure_mcp_ready()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def __enter__(self) -> AgentClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
