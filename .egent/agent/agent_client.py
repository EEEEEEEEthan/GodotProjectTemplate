"""Agent 客户端：加载配置、调用 LLM 并流式产出事件。"""

from __future__ import annotations

import asyncio
import collections.abc
import contextlib
import dataclasses
import datetime
import pathlib
import typing

import httpx
import openai

import agent.agent_config
import agent.agent_events
import agent.agent_model
import agent.agent_tools
import agent.data_loader
import agent.mcp_bridge
import agent.skill_index
import agent.tool_binding

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
    resources: contextlib.ExitStack
    log: typing.TextIO
    history: list[dict[str, typing.Any]]
    base_history_count: int
    openai_client: openai.AsyncOpenAI | None = None


@dataclasses.dataclass
class _AgentTooling:
    all_bindings: dict[str, agent.tool_binding.ToolBinding]
    skill_index: agent.skill_index.SkillIndex
    system_prompt: str
    mcp_bridge: agent.mcp_bridge.McpBridge | None = None
    mcp_schemas: dict[str, dict[str, typing.Any]] = dataclasses.field(
        default_factory=dict,
    )
    mcp_ready: bool = False


class AgentClient:
    """封装 LLM 会话、工具调用与对话历史。"""

    @staticmethod
    def load_agent(path: str) -> AgentClient:
        """从 .egent/agents/{path} 加载 agent。"""
        merged_model = agent.data_loader.load_model_toml(path)
        merged_config = agent.data_loader.load_config_toml(path)
        agent_model = agent.agent_model.AgentModel(
            api_key=AgentClient.__get_string(merged_model, "apiKey"),
            model=AgentClient.__get_string(merged_model, "model") or "gpt-4o-mini",
            base_url=AgentClient.__get_string(merged_model, "baseUrl")
            or "https://api.openai.com/v1",
        )
        agent_config = agent.agent_config.AgentConfig(
            skills=AgentClient.__get_string_array(merged_config, "skills")
            or list(agent.agent_config.DEFAULT_SKILLS),
            system_prompt=AgentClient.__get_string(merged_config, "systemPrompt")
            or agent.agent_config.DEFAULT_SYSTEM_PROMPT,
            ignore_files=AgentClient.__get_string_array(merged_config, "ignoreFiles")
            or list(agent.agent_config.DEFAULT_IGNORE_FILES),
            mcp_servers=agent.data_loader.load_mcp_servers(path),
        )
        return AgentClient(path, agent_model, agent_config)

    @staticmethod
    def __get_string(data: dict, key: str) -> str | None:
        value = data.get(key)
        return value if isinstance(value, str) else None

    @staticmethod
    def __get_string_array(data: dict, key: str) -> list[str] | None:
        value = data.get(key)
        if not isinstance(value, list):
            return None
        return [item for item in value if isinstance(item, str)]

    def __init__(
        self,
        name: str,
        model: agent.agent_model.AgentModel,
        config: agent.agent_config.AgentConfig,
        *,
        tools: list[agent.tool_binding.ToolHandler] | None = None,
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
        self.__tools: list[agent.tool_binding.ToolHandler] = (
            list(tools) if tools is not None else []
        )
        self.__tooling = self.__build_tooling(config)

        self.__conversation.history.append(
            {"role": "system", "content": self.__tooling.system_prompt}
        )
        self.__conversation.base_history_count = len(self.__conversation.history)

    def __open_conversation(self) -> _ConversationState:
        log_directory = agent.data_loader.EGENT_TEMP_DIR
        log_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        resources = contextlib.ExitStack()
        log_file = resources.enter_context(
            open(
                log_directory / f"{self.name}_{timestamp}.log",
                "a",
                encoding="utf-8",
                buffering=1,
            )
        )
        return _ConversationState(
            resources=resources,
            log=log_file,
            history=[],
            base_history_count=0,
        )

    def __compose_system_prompt(
        self,
        base_prompt: str,
        all_bindings: dict[str, agent.tool_binding.ToolBinding],
    ) -> str:
        parts: list[str] = []
        if "skill_tool_learn_skill" in all_bindings:
            parts.append(self.skill_index.prompt)
        parts.append(base_prompt)
        return "\n\n".join(
            part.strip()
            for part in parts
            if part.strip()
        )

    def __build_tooling(self, config: agent.agent_config.AgentConfig) -> _AgentTooling:
        all_bindings = agent.tool_binding.bind_tools(*self.__tools)
        mcp_bridge_instance = (
            agent.mcp_bridge.McpBridge(config.mcp_servers)
            if config.mcp_servers
            else None
        )
        return _AgentTooling(
            all_bindings=all_bindings,
            skill_index=self.skill_index,
            system_prompt=self.__compose_system_prompt(
                config.system_prompt,
                all_bindings,
            ),
            mcp_bridge=mcp_bridge_instance,
        )

    async def __ensure_mcp_ready(self) -> None:
        tooling = self.__tooling
        if tooling.mcp_bridge is None or tooling.mcp_ready:
            return
        await tooling.mcp_bridge.start()
        tooling.mcp_schemas = tooling.mcp_bridge.all_schemas()
        tooling.mcp_ready = True

    def __resolve_active_bindings(
        self,
        tools: list[agent.tool_binding.ToolHandler] | None,
    ) -> dict[str, agent.tool_binding.ToolBinding]:
        if tools is not None:
            return agent.tool_binding.bind_tools(*tools)
        return dict(self.__tooling.all_bindings)

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

    async def prepare(self) -> None:
        """启动 MCP 并刷新可用工具列表。"""
        await self.__ensure_mcp_ready()

    async def summarize(self) -> None:
        """将当前对话历史压缩为摘要并替换旧消息。"""
        conversation = self.__conversation
        if len(conversation.history) <= conversation.base_history_count:
            return

        client = self.__get_or_create_client()
        summarization_history = list(conversation.history)
        summarization_history.append(
            {
                "role": "user",
                "content": "请将以上对话压缩为简洁摘要，保留关键决策、结论、未完成任务与重要上下文。",
            }
        )
        response = await client.chat.completions.create(
            model=self.__model.model,
            messages=summarization_history,
        )
        summary = response.choices[0].message.content or ""
        del conversation.history[conversation.base_history_count :]
        if summary:
            conversation.history.append({"role": "assistant", "content": summary})

    async def send(
        self,
        role: str,
        prompt: str,
        *,
        add_to_history: bool = True,
        tools: list[agent.tool_binding.ToolHandler] | None = None,
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        """发送单条消息并流式返回事件。"""
        async for event in self.send_messages(
            [{"role": role, "content": prompt}],
            add_to_history=add_to_history,
            tools=tools,
        ):
            yield event

    async def send_messages(
        self,
        contents: list[dict[str, typing.Any]],
        *,
        add_to_history: bool = True,
        tools: list[agent.tool_binding.ToolHandler] | None = None,
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
                    conversation.log.write(f"[{role}]\n{content}\n\n")

        active_bindings = self.__resolve_active_bindings(tools)
        per_send_override = tools is not None
        advertised_tools = self.__build_advertised_tools(
            active_bindings,
            include_mcp=not per_send_override,
        )
        invoke = self.__build_invoke(
            active_bindings,
            include_mcp=not per_send_override,
        )

        text_buffer: list[str] = []
        async for event in self.__run_turn(
            chat_history,
            text_buffer,
            advertised_tools,
            invoke,
            active_bindings,
        ):
            if add_to_history:
                if isinstance(event, agent.agent_events.TextDelta):
                    conversation.log.write(event.text)
                elif isinstance(event, agent.agent_events.ToolInvoked):
                    conversation.log.write("\n")
                    tool_header = (
                        f"[{event.name}]"
                        if not event.arguments
                        else (
                            f"[{event.name}] "
                            f"{agent.agent_tools.format_tool_arguments(event.arguments)}"
                        )
                    )
                    conversation.log.write(f"{tool_header}\n")
                    if event.result:
                        conversation.log.write(f"{event.result}\n")
            yield event

        if add_to_history:
            reply = "".join(text_buffer)
            if reply and not (
                conversation.history
                and conversation.history[-1].get("role") == "assistant"
                and conversation.history[-1].get("content") == reply
            ):
                conversation.history.append({"role": "assistant", "content": reply})
            conversation.log.write("\n")
            conversation.log.flush()

    async def __run_turn(
        self,
        messages: list[dict[str, typing.Any]],
        text_buffer: list[str],
        advertised_tools: list[dict[str, typing.Any]],
        invoke: typing.Callable[
            [str, dict[str, typing.Any]],
            collections.abc.Awaitable[str],
        ],
        active_bindings: dict[str, agent.tool_binding.ToolBinding],
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
                active_bindings,
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
        active_bindings: dict[str, agent.tool_binding.ToolBinding],
    ) -> collections.abc.AsyncIterator[agent.agent_events.ToolInvoked]:
        for tool_call in tool_calls:
            openai_name = tool_call["function"]["name"]
            arguments = agent.agent_tools.parse_tool_arguments(
                tool_call["function"]["arguments"],
            )
            result = await invoke(openai_name, arguments)
            tool_name = (
                openai_name
                if openai_name in active_bindings
                or openai_name in self.__tooling.mcp_schemas
                else openai_name
            )
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
    def tools(self) -> list[agent.tool_binding.ToolHandler]:
        """当前 agent 注册的全部工具方法。"""
        return list(self.__tools)

    @tools.setter
    def tools(self, handlers: list[agent.tool_binding.ToolHandler]) -> None:
        self.__tools = list(handlers)
        self.__tooling.all_bindings = agent.tool_binding.bind_tools(*self.__tools)
        self.__tooling.system_prompt = self.__compose_system_prompt(
            self.config.system_prompt,
            self.__tooling.all_bindings,
        )
        if (
            self.__conversation.history
            and self.__conversation.history[0].get("role") == "system"
        ):
            self.__conversation.history[0]["content"] = self.__tooling.system_prompt

    @property
    def system_prompt(self) -> str:
        """合并 skill 提示后的完整系统提示词。"""
        return self.__tooling.system_prompt

    @property
    def tool_whitelist(self) -> list[str]:
        """当前 agent 可调用工具名（内置 + MCP）。"""
        tooling = self.__tooling
        names = sorted(tooling.all_bindings)
        for openai_name in sorted(tooling.mcp_schemas):
            if openai_name not in tooling.all_bindings:
                names.append(openai_name)
        return names

    @property
    def model(self) -> str:
        """LLM 模型名。"""
        return self.__model.model

    @property
    def base_url(self) -> str:
        """OpenAI 兼容 API 的 base URL。"""
        return self.__model.base_url.strip() or "https://api.openai.com/v1"

    async def aclose(self) -> None:
        """关闭 MCP 连接与会话日志。"""
        tooling = self.__tooling
        if tooling.mcp_bridge is not None and tooling.mcp_ready:
            await tooling.mcp_bridge.close()
            tooling.mcp_ready = False
        self.__conversation.resources.close()

    def close(self) -> None:
        """关闭会话日志文件。"""
        self.__conversation.resources.close()

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

    def __enter__(self) -> AgentClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        tooling = self.__tooling
        if tooling.mcp_bridge is not None and tooling.mcp_ready:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(self.aclose())
                return
        self.close()
