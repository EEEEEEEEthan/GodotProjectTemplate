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


def discover_test_scripts() -> list[pathlib.Path]:
    """从 egent_handlers/tests/*_test.gd 自动发现测试脚本。"""
    return sorted(TESTS_DIR.glob("*_test.gd"))


def resolve_script_res_path(script_path: str) -> str:
    """将项目内 GD 脚本路径规范为 res:// 路径。"""
    if script_path.startswith("res://"):
        return script_path

    path = pathlib.Path(script_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()

    try:
        relative = path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"脚本路径不在项目内: {script_path}") from error

    if relative.suffix.lower() != ".gd":
        raise ValueError(f"不是 GD 脚本: {script_path}")

    if not path.is_file():
        raise FileNotFoundError(f"脚本不存在: {script_path}")

    return "res://" + relative.as_posix()


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


def _execute_test(
    res_path: str,
    *,
    headless: bool = False,
    timeout_seconds: int = 120,
) -> tuple[int, str]:
    """运行单个测试，返回 (退出码, 合并输出)。"""
    if not ENGINE_EXE.exists():
        return 1, f"引擎不存在: {ENGINE_EXE}"

    with tempfile.TemporaryDirectory(prefix="engine-test-") as temp_dir:
        temp_path = pathlib.Path(temp_dir)
        log_file = temp_path / "stdout.log"
        stderr_file = temp_path / "stderr.log"

        engine_args = ["--script", TEST_SCRIPT]
        if headless:
            engine_args.append("--headless")
        engine_args.extend(["--", "--autotest", res_path])

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
                    combined_output = _read_combined_output(log_file, stderr_file)
                    return 1, combined_output + f"\nEngine test timed out after {timeout_seconds}s"

                combined_output = _read_combined_output(log_file, stderr_file)
                if ERROR_PATTERN.search(combined_output):
                    process.kill()
                    process.wait()
                    return 1, combined_output

                time.sleep(0.2)

            exit_code = process.returncode or 0

        combined_output = _read_combined_output(log_file, stderr_file)
        if ERROR_PATTERN.search(combined_output):
            return 1, combined_output
        return exit_code, combined_output


def run_test(
    script_path: str,
    *,
    headless: bool = False,
    ignore_prepare: bool = False,
    timeout_seconds: int = 120,
) -> int:
    """运行指定 GD 脚本自动化测试，返回进程退出码。"""
    try:
        res_path = resolve_script_res_path(script_path)
    except (ValueError, FileNotFoundError) as error:
        print(str(error), file=sys.stderr)
        return 1

    if not ignore_prepare:
        exit_code = prepare_engine()
        if exit_code != 0:
            return exit_code

    exit_code, combined_output = _execute_test(
        res_path,
        headless=headless,
        timeout_seconds=timeout_seconds,
    )
    sys.stdout.write(combined_output)
    return exit_code


def run_tests(script_path: str, *, headless: bool = False) -> int:
    """运行指定 GD 脚本自动化测试。"""
    return run_test(script_path, headless=headless)


def run_test_report(
    script_path: str,
    *,
    headless: bool = False,
) -> tuple[bool, str]:
    """运行单个测试，返回 (是否通过, 汇总信息)。"""
    try:
        res_path = resolve_script_res_path(script_path)
    except (ValueError, FileNotFoundError) as error:
        return False, str(error)

    exit_code = prepare_engine()
    if exit_code != 0:
        return False, f"引擎准备失败 (exit code: {exit_code})"

    exit_code, combined_output = _execute_test(res_path, headless=headless)
    display_name = res_path.removeprefix("res://")
    status = "PASS" if exit_code == 0 else "FAIL"
    lines = [f"[{status}] {display_name} (exit code: {exit_code})"]
    if exit_code != 0 and combined_output.strip():
        lines.append(combined_output.strip())
    return exit_code == 0, "\n".join(lines)


def run_all(*, headless: bool = True, verbose: bool = False) -> tuple[bool, str]:
    """运行 egent_handlers/tests/ 下全部测试，返回 (是否全部通过, 汇总信息)。"""
    test_files = discover_test_scripts()
    if not test_files:
        message = "未找到任何 *_test.gd 测试文件"
        if verbose:
            print(message)
        return True, message

    exit_code = prepare_engine()
    if exit_code != 0:
        message = f"引擎准备失败 (exit code: {exit_code})"
        if verbose:
            print(message)
        return False, message

    results: list[tuple[str, int, str]] = []
    for test_file in test_files:
        test_name = test_file.relative_to(PROJECT_ROOT).as_posix()
        if verbose:
            print(f"[RUN] {test_name}")

        try:
            res_path = resolve_script_res_path(test_name)
            exit_code, combined_output = _execute_test(res_path, headless=headless)
            detail = combined_output.strip() if exit_code != 0 else ""
            results.append((test_name, exit_code, detail))
            if verbose:
                status = "PASS" if exit_code == 0 else "FAIL"
                sys.stdout.write(combined_output)
                print(f"[{status}] {test_name} (exit code: {exit_code})")
                print()
        except (ValueError, FileNotFoundError) as error:
            detail = str(error)
            results.append((test_name, 1, detail))
            if verbose:
                print(f"[FAIL] {test_name} ({detail})")
                print()

    all_pass = all(code == 0 for _, code, _ in results)
    lines: list[str] = []
    if verbose:
        print("=== 汇总 ===")
    for name, code, detail in results:
        status = "PASS" if code == 0 else "FAIL"
        line = f"[{status}] {name} (exit code: {code})"
        lines.append(line)
        if verbose:
            print(f"  {line}")
        if code != 0 and detail:
            lines.append(detail)

    total = len(results)
    passed = sum(1 for _, code, _ in results if code == 0)
    summary = f"总计: {total} 测试, {passed} 通过, {total - passed} 失败"
    lines.append(summary)
    if verbose:
        print(f"\n{summary}")

    return all_pass, "\n".join(lines)
