"""测试当轮上下文裁剪逻辑。"""

from __future__ import annotations

import sys

from _test_setup import *  # noqa: F401

import agent.agent_client


def test_trim_omits_older_tool_results() -> None:
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]},
        {"role": "tool", "content": "a" * 80_000, "tool_call_id": "1"},
        {"role": "assistant", "content": None, "tool_calls": [{"id": "2"}]},
        {"role": "tool", "content": "recent", "tool_call_id": "2"},
    ]

    trimmed = agent.agent_client.AgentClient._AgentClient__trim_inflight_context(
        messages,
        10_000,
    )

    assert trimmed is True
    assert messages[3]["content"] == agent.agent_client._TOOL_RESULT_OMITTED
    assert messages[5]["content"] == "recent"


def main() -> int:
    test_trim_omits_older_tool_results()
    print("PASS test_context_trim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
