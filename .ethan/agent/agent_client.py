"""Agent 客户端：加载配置、调用 LLM 并流式产出事件。"""

from __future__ import annotations

import collections.abc
import contextlib
import dataclasses
import datetime
import pathlib
import typing

import openai

import agent.agent_config
import agent.agent_events
import agent.agent_model
import agent.agent_tools
import agent.data_loader
import agent.skill_index
import agent.tools.file_edit_tool
import agent.tools.grep_search_tool
import agent.tools.memory_tool
import agent.tools.read_file_tool
import agent.tools.skill_tool
import agent.tools.system_info_tool
import agent.tools.walk_files_tool


@dataclasses.dataclass
class _ConversationState:
    resources: contextlib.ExitStack
    log: typing.TextIO
    history: list[dict[str, typing.Any]]
    base_history_count: int
    openai_client: openai.AsyncOpenAI | None = None


@dataclasses.dataclass
class _AgentTooling:
    whitelist: list[str]
    advertised_tools: list[dict[str, typing.Any]]
    skill_index: agent.skill_index.SkillIndex
    system_prompt: str
    invoke: typing.Callable[[str, dict[str, typing.Any]], collections.abc.Awaitable[str]]


class AgentClient:
    """封装 LLM 会话、工具调用与对话历史。"""

    @staticmethod
    def load_agent(path: str) -> AgentClient:
        """从 .ethan/agents/{path} 加载 agent。"""
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
            tool_whitelist=AgentClient.__get_string_array(merged_config, "tools")
            or list(agent.agent_tools.FULL_TOOL_LIST),
            system_prompt=AgentClient.__get_string(merged_config, "systemPrompt")
            or agent.agent_config.DEFAULT_SYSTEM_PROMPT,
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
    ) -> None:
        if not name or not name.strip():
            raise ValueError("name 不能为空")
        if not config.system_prompt or not config.system_prompt.strip():
            raise ValueError("system_prompt 不能为空")

        self.name = name.strip()
        self.__model = model
        self.__conversation = self.__open_conversation()
        self.__tooling = self.__build_tooling(config)

        self.__conversation.history.append(
            {"role": "system", "content": self.__tooling.system_prompt}
        )
        self.__conversation.base_history_count = len(self.__conversation.history)

    def __open_conversation(self) -> _ConversationState:
        log_directory = pathlib.Path.cwd() / ".ethan" / ".temp"
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

    def __build_tooling(self, config: agent.agent_config.AgentConfig) -> _AgentTooling:
        tool_whitelist = list(config.tool_whitelist)
        skill_index = agent.skill_index.SkillIndex(config.skills)
        system_prompt_parts: list[str] = []
        if "skill_tool_learn_skill" in tool_whitelist:
            system_prompt_parts.append(skill_index.prompt)
        system_prompt_parts.append(config.system_prompt)
        system_prompt = "\n\n".join(
            part.strip()
            for part in system_prompt_parts
            if part.strip()
        )
        skill_tool = agent.tools.skill_tool.SkillTool(skill_index, self.name)
        memory_tool = agent.tools.memory_tool.MemoryTool(self.name)
        return _AgentTooling(
            whitelist=tool_whitelist,
            advertised_tools=agent.agent_tools.select_advertised_tools(tool_whitelist),
            skill_index=skill_index,
            system_prompt=system_prompt,
            invoke=agent.agent_tools.build_tool_dispatch(
                {
                    "skill_tool_learn_skill": skill_tool.learn_skill,
                    "skill_tool_run_skill_script": skill_tool.run_skill_script,
                    "file_edit_tool_create_file": (
                        agent.tools.file_edit_tool.FileEditTool.create_file
                    ),
                    "file_edit_tool_apply_patch": (
                        agent.tools.file_edit_tool.FileEditTool.apply_patch
                    ),
                    "grep_search_tool_grep_search": (
                        agent.tools.grep_search_tool.GrepSearchTool.grep_search
                    ),
                    "walk_files_tool_walk_files": (
                        agent.tools.walk_files_tool.WalkFilesTool.walk_files
                    ),
                    "system_info_tool_system_info": (
                        agent.tools.system_info_tool.SystemInfoTool.system_info
                    ),
                    "memory_tool_add_item": memory_tool.add_item,
                    "memory_tool_remove_item": memory_tool.remove_item,
                    "memory_tool_update_item": memory_tool.update_item,
                    "memory_tool_list_items": memory_tool.list_items,
                    "memory_tool_find_str": memory_tool.find_str,
                    "read_file_tool_read_file_outline_cs": (
                        agent.tools.read_file_tool.ReadFileTool.read_file_outline_cs
                    ),
                    "read_file_tool_read_file_outline_md": (
                        agent.tools.read_file_tool.ReadFileTool.read_file_outline_md
                    ),
                    "read_file_tool_read_lines": (
                        agent.tools.read_file_tool.ReadFileTool.read_lines
                    ),
                    "read_file_tool_read_whole_file": (
                        agent.tools.read_file_tool.ReadFileTool.read_whole_file
                    ),
                }
            ),
        )

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
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        """发送单条消息并流式返回事件。"""
        async for event in self.send_messages(
            [{"role": role, "content": prompt}],
            add_to_history=add_to_history,
        ):
            yield event

    async def send_messages(
        self,
        contents: list[dict[str, typing.Any]],
        *,
        add_to_history: bool = True,
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        """发送多条消息，可选写入历史与日志。"""
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

        text_buffer: list[str] = []
        async for event in self.__run_turn(chat_history, text_buffer):
            if add_to_history:
                if isinstance(event, agent.agent_events.TextDelta):
                    conversation.log.write(event.text)
                elif isinstance(event, agent.agent_events.ToolInvoked):
                    conversation.log.write("\n")
                    tool_header = (
                        f"[{event.name}]"
                        if not event.arguments
                        else f"[{event.name}] {event.arguments}"
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
    ) -> collections.abc.AsyncIterator[agent.agent_events.AgentEvent]:
        client = self.__get_or_create_client()

        while True:
            turn_text: list[str] = []
            tool_calls_by_index: dict[int, dict[str, typing.Any]] = {}

            stream = await client.chat.completions.create(
                model=self.__model.model,
                messages=messages,
                tools=self.__tooling.advertised_tools or None,
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
                        AgentClient.__merge_tool_call_delta(tool_calls_by_index, tool_call)

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

            async for event in self.__invoke_tool_calls(tool_calls, messages):
                yield event

    async def __invoke_tool_calls(
        self,
        tool_calls: list[dict[str, typing.Any]],
        messages: list[dict[str, typing.Any]],
    ) -> collections.abc.AsyncIterator[agent.agent_events.ToolInvoked]:
        for tool_call in tool_calls:
            openai_name = tool_call["function"]["name"]
            arguments = agent.agent_tools.parse_tool_arguments(
                tool_call["function"]["arguments"],
            )
            result = await self.__tooling.invoke(openai_name, arguments)
            tool_name = agent.agent_tools.resolve_tool_name(openai_name) or openai_name
            yield agent.agent_events.ToolInvoked(
                tool_name,
                agent.agent_tools.format_tool_arguments(arguments),
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
    def system_prompt(self) -> str:
        """合并 skill 提示后的完整系统提示词。"""
        return self.__tooling.system_prompt

    @property
    def tool_whitelist(self) -> list[str]:
        """当前 agent 允许调用的工具白名单。"""
        return list(self.__tooling.whitelist)

    @property
    def model(self) -> str:
        """LLM 模型名。"""
        return self.__model.model

    @property
    def base_url(self) -> str:
        """OpenAI 兼容 API 的 base URL。"""
        return self.__model.base_url.strip() or "https://api.openai.com/v1"

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
        self.close()
