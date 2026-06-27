import asyncio

import loop.wrapped_agent


async def run(prompt: str) -> None:
    agent = await loop.wrapped_agent.get_agent("jason")
    while True:
        await agent.send(prompt)
        


if __name__ == "__main__":
    asyncio.run(run("检查自身能力并列出改进点"))
