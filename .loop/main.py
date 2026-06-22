"""Dev Loop 控制台入口。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bridge_host import BridgeHost
from config import PROJECT_ROOT
from orchestrator import WorkflowOrchestrator


def main() -> None:
    with BridgeHost.open(PROJECT_ROOT) as bridge_host:
        WorkflowOrchestrator(client=bridge_host.client).run()


if __name__ == "__main__":
    main()
