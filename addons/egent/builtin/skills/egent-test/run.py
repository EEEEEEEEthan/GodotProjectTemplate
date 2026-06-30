"""运行 egent 测试套件。从项目根目录调用 run_all_tests.py。"""

from __future__ import annotations

import pathlib
import subprocess
import sys


def main() -> int:
    project_root = pathlib.Path(__file__).resolve().parents[5]
    run_all = project_root / "addons" / "egent" / "builtin" / "test" / "run_all_tests.py"
    result = subprocess.run([sys.executable, str(run_all)], cwd=project_root)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
