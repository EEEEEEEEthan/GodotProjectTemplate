"""Godot 自动化测试运行器。"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
TESTS_DIR = PROJECT_ROOT / "egent_handlers" / "tests"
ENGINE_EXE = PROJECT_ROOT / ".engine" / ".engine.exe"
PREPARE_BAT = PROJECT_ROOT / ".engine-prepare.bat"
TEST_SCRIPT = "res://addons/egent/test.gd"
ERROR_PATTERN = re.compile(r"SCRIPT ERROR:|Parse Error:|ERROR: Failed")


def discover_test_names() -> list[str]:
    """从 egent_handlers/tests/*_test.gd 自动发现测试名。"""
    return [
        path.stem.removesuffix("_test")
        for path in sorted(TESTS_DIR.glob("*_test.gd"))
    ]


def prepare_engine() -> int:
    """下载/准备引擎并执行 --import。"""
    result = subprocess.run(
        ["cmd", "/c", str(PREPARE_BAT)],
        cwd=PROJECT_ROOT,
        check=False,
    )
    if result.returncode != 0:
        return result.returncode

    if not ENGINE_EXE.exists():
        print(f"引擎不存在: {ENGINE_EXE}", file=sys.stderr)
        return 1

    result = subprocess.run(
        [str(ENGINE_EXE), "--headless", "--import"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode


def _read_combined_output(log_file: pathlib.Path, stderr_file: pathlib.Path) -> str:
    parts: list[str] = []
    if log_file.exists():
        parts.append(log_file.read_text(encoding="utf-8", errors="replace"))
    if stderr_file.exists():
        parts.append(stderr_file.read_text(encoding="utf-8", errors="replace"))
    return "".join(parts)


def _print_combined_output(log_file: pathlib.Path, stderr_file: pathlib.Path) -> None:
    for path in (log_file, stderr_file):
        if path.exists():
            sys.stdout.write(path.read_text(encoding="utf-8", errors="replace"))


def run_test(
    test_name: str,
    *,
    headless: bool = False,
    ignore_prepare: bool = False,
    timeout_seconds: int = 120,
) -> int:
    """运行单个 Godot 自动化测试，返回进程退出码。"""
    if not ignore_prepare:
        exit_code = prepare_engine()
        if exit_code != 0:
            return exit_code

    if not ENGINE_EXE.exists():
        print(f"引擎不存在: {ENGINE_EXE}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="engine-test-") as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        log_file = temp_path / "stdout.log"
        stderr_file = temp_path / "stderr.log"

        engine_args = ["--script", TEST_SCRIPT]
        if headless:
            engine_args.append("--headless")
        engine_args.extend(["--", "--autotest", test_name])

        with (
            log_file.open("w", encoding="utf-8") as stdout_handle,
            stderr_file.open("w", encoding="utf-8") as stderr_handle,
        ):
            process = subprocess.Popen(
                [str(ENGINE_EXE), *engine_args],
                cwd=PROJECT_ROOT,
                stdout=stdout_handle,
                stderr=stderr_handle,
            )

            deadline = time.monotonic() + timeout_seconds
            while process.poll() is None:
                if time.monotonic() > deadline:
                    process.kill()
                    process.wait()
                    print(f"Engine test timed out after {timeout_seconds}s")
                    _print_combined_output(log_file, stderr_file)
                    return 1

                combined_output = _read_combined_output(log_file, stderr_file)
                if ERROR_PATTERN.search(combined_output):
                    process.kill()
                    process.wait()
                    _print_combined_output(log_file, stderr_file)
                    return 1

                time.sleep(0.2)

            exit_code = process.returncode or 0

        combined_output = _read_combined_output(log_file, stderr_file)
        _print_combined_output(log_file, stderr_file)
        if ERROR_PATTERN.search(combined_output):
            return 1
        return exit_code


def run_tests(test_name: str, *, headless: bool = False) -> int:
    """运行单个或全部测试。"""
    if test_name == "all":
        exit_code = prepare_engine()
        if exit_code != 0:
            return exit_code

        names = discover_test_names()
        if not names:
            print("未找到任何 *_test.gd 测试文件", file=sys.stderr)
            return 1

        any_failed = False
        for name in names:
            print(f"=== Running test: {name} ===")
            result = run_test(name, headless=headless, ignore_prepare=True)
            if result != 0:
                print(f"[FAILED] {name}")
                any_failed = True
            else:
                print(f"[PASSED] {name}")

        if any_failed:
            print("Some tests failed")
            return 1
        print("All tests passed")
        return 0

    return run_test(test_name, headless=headless)
