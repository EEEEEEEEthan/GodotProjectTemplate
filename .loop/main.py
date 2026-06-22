"""Dev Loop 控制台入口。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridge_host import BridgeHost
from config import PROJECT_ROOT, ensure_cursor_api_key_env, load_all_role_setting_sources
from loop_log import LoopRunLogger
from orchestrator import WorkflowOrchestrator


def main() -> None:
    ensure_cursor_api_key_env()
    for role, sources in load_all_role_setting_sources().items():
        print(
            f"[settings] {role}.setting_sources={sources or '(none)'}",
            file=sys.stderr,
        )
    with LoopRunLogger.open() as run_logger:
        print(f"[log] 会话日志: {run_logger.log_path}", file=sys.stderr)
        with BridgeHost.open(PROJECT_ROOT) as bridge_host:
            WorkflowOrchestrator(
                client=bridge_host.client,
                run_logger=run_logger,
            ).run()


if __name__ == "__main__":
    main()
