"""运行 .egent 测试套件。从项目根目录调用 run_all_tests.py。"""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    run_all = project_root / ".egent" / "builtin" / "test" / "run_all_tests.py"

    print(f"项目根目录: {project_root}")
    print(f"运行: {run_all}")
    print()

    result = subprocess.run(
        [sys.executable, str(run_all)],
        cwd=project_root,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
