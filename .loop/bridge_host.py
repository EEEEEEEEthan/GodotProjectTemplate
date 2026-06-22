"""Windows 兼容的 cursor-sdk-bridge 宿主与共享 Client 生命周期。"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from cursor_sdk import Client, CursorSDKError, LocalAgentOptions
from cursor_sdk._bridge import (
    Bridge,
    BridgeEndpoint,
    _bridge_subprocess_env,
    _terminate_process,
    parse_discovery_line,
)
from cursor_sdk._local_store import LocalAgentStoreHandler
from cursor_sdk._store_callback import (
    StoreCallbackServer,
    local_store_bridge_argv,
    resolve_store_callback_handler_for_launch,
    store_callback_bridge_argv,
)
from cursor_sdk._tool_callback import ToolCallbackServer, tool_callback_bridge_argv
from cursor_sdk._vendor import resolve_bridge_path

from config import (
    BRIDGE_LAUNCH_TIMEOUT_SECONDS,
    BRIDGE_STATE_ROOT,
    PROJECT_ROOT,
    load_all_role_setting_sources,
    union_bridge_setting_sources,
)


def _read_discovery_from_stderr(
    process: subprocess.Popen[str],
    timeout: float,
) -> Mapping[str, Any]:
    """用阻塞 readline 读 discovery，避免 Windows 上 select 无法监听管道。"""
    if process.stderr is None:
        raise CursorSDKError("Bridge process stderr is unavailable")

    discovery_holder: list[Mapping[str, Any]] = []
    stderr_lines: list[str] = []
    failure_holder: list[BaseException] = []
    finished = threading.Event()

    def stderr_reader() -> None:
        try:
            assert process.stderr is not None
            for line in process.stderr:
                stderr_lines.append(line)
                try:
                    discovery = parse_discovery_line(line)
                except CursorSDKError as error:
                    failure_holder.append(error)
                    return
                if discovery is not None:
                    discovery_holder.append(discovery)
                    return
        except Exception as error:
            failure_holder.append(error)
        finally:
            finished.set()

    reader_thread = threading.Thread(
        target=stderr_reader,
        name="bridge-discovery-reader",
        daemon=True,
    )
    reader_thread.start()

    deadline = time.monotonic() + timeout
    while not finished.wait(timeout=0.1):
        if time.monotonic() >= deadline:
            _terminate_process(process)
            raise CursorSDKError(
                "Timed out waiting for bridge discovery\n"
                + "".join(stderr_lines)
            )
        exit_code = process.poll()
        if exit_code is not None:
            finished.wait(timeout=1.0)
            break

    if failure_holder:
        _terminate_process(process)
        raise failure_holder[0]

    if discovery_holder:
        return discovery_holder[0]

    exit_code = process.poll()
    raise CursorSDKError(
        f"Bridge exited before discovery with status {exit_code}: "
        + "".join(stderr_lines)
    )


class ManagedBridge(Bridge):
    """继承 SDK Bridge，仅替换 Windows 可用的 discovery 读取。"""

    @classmethod
    def launch(
        cls,
        command: str
        | os.PathLike[str]
        | Sequence[str | os.PathLike[str]]
        | None = None,
        *,
        workspace: str | os.PathLike[str] | None = None,
        state_root: str | os.PathLike[str] | None = None,
        host: str | None = None,
        port: int | None = None,
        timeout: float = BRIDGE_LAUNCH_TIMEOUT_SECONDS,
        local: LocalAgentOptions | Mapping[str, Any] | None = None,
        store_handler: LocalAgentStoreHandler | None = None,
    ) -> "ManagedBridge":
        if command is None:
            argv = [resolve_bridge_path()]
        elif isinstance(command, (str, os.PathLike)):
            argv = [os.fspath(command)]
        else:
            argv = [os.fspath(argument) for argument in command]
        if workspace:
            argv.extend(["--workspace", os.fspath(workspace)])
        if state_root:
            argv.extend(["--state-root", os.fspath(state_root)])
        if host:
            argv.extend(["--host", host])
        if port is not None:
            argv.extend(["--port", str(port)])

        store_callback_server: StoreCallbackServer | None = None
        handler = resolve_store_callback_handler_for_launch(
            local=local,
            store_handler=store_handler,
        )
        if handler is not None:
            store_callback_server = StoreCallbackServer(handler)
            argv.extend(store_callback_bridge_argv(store_callback_server.endpoint))

        tool_callback_server = ToolCallbackServer()
        argv.extend(tool_callback_bridge_argv(tool_callback_server.endpoint))
        argv.extend(local_store_bridge_argv(local))

        process = subprocess.Popen(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(_bridge_subprocess_env()),
        )
        try:
            discovery = _read_discovery_from_stderr(process, timeout)
            endpoint = BridgeEndpoint.from_discovery(discovery)
            print(
                f"[bridge] ready {endpoint.url} "
                f"(workspace={Path(workspace).name if workspace else '?'}, "
                f"pid={endpoint.pid})",
                file=sys.stderr,
            )
            return cls(
                endpoint,
                process,
                store_callback_server,
                tool_callback_server,
            )
        except Exception:
            if store_callback_server is not None:
                store_callback_server.close()
            tool_callback_server.close()
            _terminate_process(process)
            raise


class BridgeHost:
    """整条 Dev Loop 共享一个 bridge 与一个 Cursor Client。"""

    def __init__(self, client: Client, managed_bridge: ManagedBridge | None) -> None:
        self._client = client
        self._managed_bridge = managed_bridge

    @property
    def client(self) -> Client:
        return self._client

    @classmethod
    def open(
        cls,
        workspace: Path = PROJECT_ROOT,
        *,
        state_root: Path = BRIDGE_STATE_ROOT,
        timeout: float = BRIDGE_LAUNCH_TIMEOUT_SECONDS,
    ) -> "BridgeHost":
        bridge_url = os.environ.get("CURSOR_SDK_BRIDGE_URL")
        bridge_token = (
            os.environ.get("CURSOR_SDK_BRIDGE_TOKEN")
            or os.environ.get("CURSOR_SDK_BRIDGE_AUTH_TOKEN")
        )
        if bridge_url and bridge_token:
            print(f"[bridge] 连接外部 bridge: {bridge_url}", file=sys.stderr)
            client = Client.connect(bridge_url, bridge_token, max_retries=0)
            return cls(client=client, managed_bridge=None)

        state_root.mkdir(parents=True, exist_ok=True)
        setting_sources = union_bridge_setting_sources(load_all_role_setting_sources())
        local_options = LocalAgentOptions(
            cwd=str(workspace.resolve()),
            setting_sources=setting_sources,
        )
        managed_bridge = ManagedBridge.launch(
            workspace=workspace.resolve(),
            state_root=state_root.resolve(),
            timeout=timeout,
            local=local_options,
        )
        client = Client(
            managed_bridge.endpoint,
            max_retries=0,
            allow_api_key_env_fallback=True,
        )
        client._owned_bridge = managed_bridge
        return cls(client=client, managed_bridge=managed_bridge)

    def close(self) -> None:
        try:
            self._client.close()
        finally:
            if self._managed_bridge is not None:
                self._managed_bridge.close()
                self._managed_bridge = None

    def __enter__(self) -> "BridgeHost":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
