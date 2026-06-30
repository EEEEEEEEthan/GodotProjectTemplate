"""工作流工具。"""

from __future__ import annotations

import asyncio
import importlib.util
import pathlib
import typing

_BUILTIN_ROOT = pathlib.Path(__file__).resolve().parent.parent

_run_all_tests_spec = importlib.util.spec_from_file_location(
    "run_all_tests", _BUILTIN_ROOT / "test" / "run_all_tests.py"
)
_run_all_tests = importlib.util.module_from_spec(_run_all_tests_spec)
_run_all_tests_spec.loader.exec_module(_run_all_tests)


async def run_egent_development(agent_client: typing.Any, prompt: str) -> str:
    """执行egent开发工作流：委派任务给 jack

    @param prompt: 任务描述.需要包括任务原因,任务细节,关键代码位置
    """
    del agent_client
    task_prompt = prompt.strip()
    if not task_prompt:
        return "错误：prompt 不能为空。"

    import agent_definition

    nahte = None
    jack = None
    try:
        nahte = await agent_definition.get_definition("nahte").instantiate()
        jack = await agent_definition.get_definition("jack").instantiate()
        await jack.send(task_prompt)
        while True:
            # 内层 test-retry 循环，最多 10 次
            for attempt in range(10):
                tests_passed, tests_info = await asyncio.to_thread(_run_all_tests.run_all)
                if tests_passed:
                    break
                await jack.send(
                    f"你的需求是:{task_prompt}\n，很遗憾测试未通过（第{attempt+1}次）：\n{tests_info}\n请修复"
                )
            else:
                # 10 次全部失败 → 取消任务
                lst_report = await jack.send(
                    "测试未通过，我们决定取消本次工作。写一份报告，包括但不限于本次工作的简报以及遇到的问题，还有工作流上可以改进的地方(如果有的话)",
                    override_tools=(),
                )
                return "\n".join(lst_report)

            # 测试通过 → review
            lst_review = await nahte.send(
                f"jack完成了需求:\n```\n{task_prompt}\n```\n测试通过了。现在你需要根据git diff审查代码.请按照项目约定,技能等进行审查.额外注意测试代码是否正确覆盖了需求。如果审查通过，直接输出`<<<通过>>>`（三个尖括号包裹的通过），不要有任何多余的输出。否则，输出修改意见"
            )
            if lst_review and "<<<通过>>>" in lst_review[-1]:
                lst_report = await jack.send(
                    "写一份报告，包括但不限于本次工作的简报。本次工作的槽点，使用fuck工具记录。",
                    override_tools=(),
                )
                report = "\n".join(lst_report)
                return report + "\n\n任务完成。代码已审查，可以等待用户验收。"

            # review 不通过 → 修复后回到外层 while，内层 attempt 自然归零
            await jack.send(
                f"你的需求是:{task_prompt}\n，很遗憾审查未通过：\n{lst_review[-1] if lst_review else '(无输出)'}\n请修复"
            )
    except Exception as error:
        return f"错误：工作流执行失败：{error}"
    finally:
        if jack is not None:
            await jack.aclose()
        if nahte is not None:
            await nahte.aclose()
