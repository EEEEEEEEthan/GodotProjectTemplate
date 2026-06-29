"""测试 MCP 桥接生命周期与关闭容错。"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import agent.mcp_bridge as mcp_bridge_module


class _FakeSession:
  async def initialize(self) -> None:
    return None

  async def list_tools(self):
    class _Tools:
      tools: list[object] = []

    return _Tools()


@asynccontextmanager
async def _fake_stdio_client(_parameters):
  yield object(), object()


@asynccontextmanager
async def _raising_stdio_client(_parameters):
  try:
    yield object(), object()
  finally:
    raise RuntimeError(
      "Attempted to exit cancel scope in a different task than it was entered in"
    )


def test_is_mcp_shutdown_error_matches_cancel_scope_runtime_error():
  error = RuntimeError(
    "Attempted to exit cancel scope in a different task than it was entered in"
  )
  assert mcp_bridge_module._is_mcp_shutdown_error(error)


def test_is_mcp_shutdown_error_rejects_unrelated_runtime_error():
  error = RuntimeError("connection refused")
  assert not mcp_bridge_module._is_mcp_shutdown_error(error)


async def _run_close_with_fake_stdio(stdio_factory):
  original_stdio_client = mcp_bridge_module.mcp.client.stdio.stdio_client
  original_client_session = mcp_bridge_module.mcp.client.session.ClientSession

  @asynccontextmanager
  async def fake_client_session(_read_stream, _write_stream):
    yield _FakeSession()

  mcp_bridge_module.mcp.client.stdio.stdio_client = stdio_factory
  mcp_bridge_module.mcp.client.session.ClientSession = fake_client_session
  bridge = mcp_bridge_module.McpBridge(
    {
      "test": mcp_bridge_module.McpServerConfig(
        command=sys.executable,
        args=["-c", "pass"],
      )
    }
  )
  try:
    await bridge.start()
    await bridge.close()
  finally:
    mcp_bridge_module.mcp.client.stdio.stdio_client = original_stdio_client
    mcp_bridge_module.mcp.client.session.ClientSession = original_client_session


def test_close_completes_with_cancel_scope_shutdown_error():
  asyncio.run(_run_close_with_fake_stdio(_raising_stdio_client))


def test_close_completes_without_shutdown_error():
  asyncio.run(_run_close_with_fake_stdio(_fake_stdio_client))
