import pathlib
import runpy
import sys

if __package__ is None:
    addons_root = pathlib.Path(__file__).resolve().parent.parent
    if str(addons_root) not in sys.path:
        sys.path.insert(0, str(addons_root))
    runpy.run_module("egent", run_name="__main__")
else:
    from egent.cli import main

    main()
