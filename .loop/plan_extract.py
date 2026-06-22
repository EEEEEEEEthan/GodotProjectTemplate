"""从 plan mode 会话中提取 Cursor 原生 plan 文本。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from markers import extract_block

PLAN_TOOL_NAMES = frozenset({"createPlan", "create_plan"})


def _coerce_plan_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("plan", "content", "markdown", "text", "body"):
            nested = _coerce_plan_text(value.get(key))
            if nested:
                return nested
    return None


def _plan_from_tool_mapping(data: Mapping[str, Any]) -> str | None:
    tool_name = (
        data.get("name")
        or data.get("toolName")
        or data.get("tool_name")
        or data.get("type")
    )
    if tool_name not in PLAN_TOOL_NAMES:
        return None

    args = data.get("args")
    if isinstance(args, Mapping):
        plan = _coerce_plan_text(args.get("plan"))
        if plan:
            return plan

    result = data.get("result")
    if isinstance(result, Mapping):
        success = result.get("success")
        if isinstance(success, Mapping):
            plan = _coerce_plan_text(success.get("plan"))
            if plan:
                return plan
        plan = _coerce_plan_text(result.get("plan"))
        if plan:
            return plan

    return _coerce_plan_text(result)


def _walk_for_plan(value: Any, *, latest: list[str]) -> None:
    if isinstance(value, Mapping):
        plan = _plan_from_tool_mapping(value)
        if plan:
            latest.append(plan)
            return
        for nested in value.values():
            _walk_for_plan(nested, latest=latest)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _walk_for_plan(item, latest=latest)


def _latest_plan_from_payload(value: Any) -> str | None:
    found: list[str] = []
    _walk_for_plan(value, latest=found)
    return found[-1] if found else None


def extract_plan_from_run_conversation(run: Any) -> str | None:
    try:
        conversation = run.conversation()
    except Exception:
        return None

    latest: list[str] = []
    for turn in conversation:
        if getattr(turn, "type", None) != "agentConversationTurn":
            continue
        turn_payload = turn.turn
        steps = getattr(turn_payload, "steps", None) or ()
        for step in steps:
            if getattr(step, "type", None) != "toolCall":
                continue
            message = getattr(step, "message", None)
            if isinstance(message, Mapping):
                plan = _plan_from_tool_mapping(message)
                if plan:
                    latest.append(plan)
    return latest[-1] if latest else None


def extract_plan_from_agent_messages(agent: Any) -> str | None:
    try:
        messages = agent.list_messages()
    except Exception:
        return None

    latest: list[str] = []
    for item in messages:
        message = getattr(item, "message", None)
        plan = _latest_plan_from_payload(message)
        if plan:
            latest.append(plan)
    return latest[-1] if latest else None


def extract_structured_blocks(text: str) -> str | None:
    parts: list[str] = []
    for block_name in ("REQUIREMENTS", "DESIGN", "DESIGN_REVISION"):
        content = extract_block(text, block_name)
        if content:
            parts.append(f"## {block_name}\n{content}")
    if not parts:
        return None
    return "\n\n".join(parts)


def extract_plan(*, run: Any, agent: Any, response_text: str = "") -> str | None:
    """优先 Cursor 原生 createPlan，其次结构化块。"""
    for extractor in (
        lambda: extract_plan_from_agent_messages(agent),
        lambda: extract_plan_from_run_conversation(run),
    ):
        plan = extractor()
        if plan:
            return plan
    return extract_structured_blocks(response_text)
