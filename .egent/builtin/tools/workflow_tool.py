"""工作流工具。"""

from __future__ import annotations

import typing


async def run_self_upgrade(agent_client: typing.Any, prompt: str) -> str:
    """启动自升级工作流：委派任务给 nahte agent，轮询测试直至通过并返回工作报告。

    @param prompt: 升级任务描述
    """
    del agent_client
    task_prompt = prompt.strip()
    if not task_prompt:
        return "错误：prompt 不能为空。"

    import workflow_self_upgrade

    return await workflow_self_upgrade.run(task_prompt)
