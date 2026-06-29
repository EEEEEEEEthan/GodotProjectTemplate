"""自升级 workflow：发送任务后轮询测试直至通过。"""

import asyncio
import importlib.util
import pathlib
import sys

_BUILTIN_ROOT = pathlib.Path(__file__).resolve().parent

# 通过文件路径直接加载 run_all_tests，避免 sys.path hack
_run_all_tests_spec = importlib.util.spec_from_file_location(
    "run_all_tests", _BUILTIN_ROOT / "test" / "run_all_tests.py"
)
_run_all_tests = importlib.util.module_from_spec(_run_all_tests_spec)
_run_all_tests_spec.loader.exec_module(_run_all_tests)

from _console import read_prompt


async def run(prompt: str) -> str:
    """执行自升级工作流：委派任务给 nahte，轮询测试直至通过。"""
    import agent_definition
    nahte = await agent_definition.get_definition("nahte").instantiate()
    jack = await agent_definition.get_definition("jack").instantiate()
    try:
        await jack.send(prompt)
        i = 0
        while True:
            tests_passed, tests_info = await asyncio.to_thread(_run_all_tests.run_all)
            if tests_passed:
                lst_report = await jack.send(
                    "写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                    override_tools=(),
                )
                lst_review = await nahte.send(f"jack完成了需求:{prompt}\n,测试通过了。现在你需要审查代码。如果审查通过，直接输出通过二字，不要有任何多余的输出。否则，输出修改意见")
                if "通过" in lst_review[-1]:
                    return "\n".join(lst_report) + "任务完成，请根据git diff审查修改"
                await jack.send(f"你的需求是:{prompt}\n，很遗憾审查未通过：\n{lst_review[-1]}\n请修复")
                continue
            i += 1
            if i < 5:
                await jack.send(f"你的需求是:{prompt}\n，很遗憾测试未通过：\n{tests_info}\n请修复")
                continue
            lst_report = await jack.send(
                "测试未通过，我们决定取消本次工作。写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                override_tools=()
            )
            return "\n".join(lst_report)
    finally:
        await jack.aclose()


if __name__ == "__main__":
    prompt = read_prompt()
    if prompt is None or not prompt.strip():
        sys.exit(0)
    asyncio.run(run(prompt))
