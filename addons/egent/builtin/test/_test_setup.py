"""Shared test setup: adds builtin/ to sys.path so test files can import agent/tools modules.

Each test file should import this at the top:  from _test_setup import *  # noqa: F401
"""
import os
import pathlib
import sys

os.environ.setdefault("EGENT_NO_LOG", "1")

_builtin_dir = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_builtin_dir))
