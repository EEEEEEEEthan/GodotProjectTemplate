import asyncio
import agent_config
import test

async def run(prompt: str) -> str:
    agent = await agent_config.get_definition("jason").instantiate()
    await agent.send(prompt)
    for _ in range(3):
        tests_passed, tests_info = await asyncio.to_thread(test.run_all_tests.run_all)
        if not tests_passed:
            await agent.send(f"测试未通过，请修复：\n{tests_info}")
        else:
            return "执行完毕"
    return "执行失败"

if __name__ == "__main__":
    asyncio.run(run("检查自身能力并列出改进点"))
