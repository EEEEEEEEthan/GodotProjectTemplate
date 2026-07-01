"""从任意工作目录启动：python addons/egent/chat.py"""

import pathlib
import runpy
import sys

if __name__ == "__main__":
    addons_root = pathlib.Path(__file__).resolve().parent.parent
    if str(addons_root) not in sys.path:
        sys.path.insert(0, str(addons_root))
    runpy.run_module("egent", run_name="__main__")
