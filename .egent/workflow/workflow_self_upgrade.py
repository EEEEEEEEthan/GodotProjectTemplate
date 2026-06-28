"""自升级 workflow：发送任务后轮询测试直至通过。"""

import asyncio
import importlib.util
import pathlib
import sys

_EGENT_ROOT = pathlib.Path(__file__).resolve().parent.parent

# 通过文件路径直接加载 run_all_tests，避免 sys.path hack
_run_all_tests_spec = importlib.util.spec_from_file_location(
    "run_all_tests", _EGENT_ROOT / "test" / "run_all_tests.py"
)
_run_all_tests = importlib.util.module_from_spec(_run_all_tests_spec)
_run_all_tests_spec.loader.exec_module(_run_all_tests)


def read_prompt() -> str | None:
    sys.stdout.write("> ")
    sys.stdout.flush()
    line = sys.stdin.readline()
    if not line:
        return None
    return line.rstrip("\r\n")


async def run(prompt: str) -> str:
    import workflow.agent_definition

    agent = await workflow.agent_definition.get_definition("nahte").instantiate()
    try:
        await agent.send(prompt)
        i = 0
        while True:
            tests_passed, tests_info = await asyncio.to_thread(_run_all_tests.run_all)
            if tests_passed:
                lst = await agent.send(
                    "写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                    override_tools=(),
                )
                return "\n".join(lst) + "任务完成，请根据git diff审查修改"
            i += 1
            if i < 5:
                await agent.send(f"你的需求是:{prompt}\n，很遗憾测试未通过：\n{tests_info}\n请修复")
                continue
            lst = await agent.send(
                "测试未通过，我们决定取消本次工作。写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                override_tools=()
            )
            return "\n".join(lst)
    finally:
        await agent.aclose()
    return "执行失败"


if __name__ == "__main__":
    prompt = read_prompt()
    if prompt is None or not prompt.strip():
        sys.exit(0)
    asyncio.run(run(prompt))
