"""Dev Loop 控制台入口。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridge_host import BridgeHost
from config import PROJECT_ROOT, load_all_role_setting_sources
from orchestrator import WorkflowOrchestrator


def main() -> None:
    for role, sources in load_all_role_setting_sources().items():
        print(
            f"[settings] {role}.setting_sources={sources or '(none)'}",
            file=sys.stderr,
        )
    with BridgeHost.open(PROJECT_ROOT) as bridge_host:
        WorkflowOrchestrator(client=bridge_host.client).run()


if __name__ == "__main__":
    main()
