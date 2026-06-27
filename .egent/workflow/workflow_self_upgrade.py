"""自升级 workflow：发送任务后轮询测试直至通过。"""

import asyncio
import pathlib
import sys

_EGENT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_EGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EGENT_ROOT))

_TEST_DIR = _EGENT_ROOT / "test"
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

import run_all_tests
import workflow.agent_config



def read_prompt() -> str | None:
    sys.stdout.write("> ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n")


async def run(prompt: str) -> str:
    agent = await workflow.agent_config.get_definition("nahte").instantiate()
    try:
        await agent.send(prompt)
        for _ in range(3):
            tests_passed, tests_info = await asyncio.to_thread(run_all_tests.run_all)
            if tests_passed:
                agent.tools = []
                lst = await agent.send("写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)")
                return "\n".join(lst)
            await agent.send(f"测试未通过，请修复：\n{tests_info}")
    finally:
        await agent.aclose()
    return "执行失败"


if __name__ == "__main__":
    prompt = read_prompt()
    if prompt is None or not prompt.strip():
        sys.exit(0)
    asyncio.run(run(prompt))
