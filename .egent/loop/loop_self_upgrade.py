import asyncio
import pathlib
import sys

_EGENT_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_EGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(_EGENT_ROOT))
_TEST_DIR = _EGENT_ROOT / "test"
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

import loop.wrapped_agent
import run_all_tests

async def run(prompt: str) -> str:
    agent = await loop.wrapped_agent.get_agent("jason")
    await agent.send(prompt)
    for _ in range(3):
        tests_passed, tests_info = await asyncio.to_thread(run_all_tests.run_all)
        if not tests_passed:
            await agent.send(f"测试未通过，请修复：\n{tests_info}")
        else:
            return "执行完毕"
    return "执行失败"

if __name__ == "__main__":
    asyncio.run(run("检查自身能力并列出改进点"))
