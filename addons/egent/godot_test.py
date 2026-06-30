"""Godot 自动化测试运行器。"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
ENGINE_EXE = PROJECT_ROOT / ".engine" / ".engine.exe"
PREPARE_BAT = PROJECT_ROOT / ".engine-prepare.bat"
TEST_SCRIPT = "res://addons/egent/test.gd"
ERROR_PATTERN = re.compile(r"SCRIPT ERROR:|Parse Error:|ERROR: Failed")


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


def resolve_folder_path(folder_path: str) -> pathlib.Path:
    """将项目内文件夹路径规范为绝对路径。"""
    path = pathlib.Path(folder_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path = path.resolve()

    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as error:
        raise ValueError(f"文件夹路径不在项目内: {folder_path}") from error

    if not path.is_dir():
        raise NotADirectoryError(f"文件夹不存在: {folder_path}")

    return path


def discover_gd_scripts(folder_path: str) -> list[pathlib.Path]:
    """发现文件夹下所有 .gd 文件。"""
    return sorted(resolve_folder_path(folder_path).glob("*.gd"))


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


def _format_result(display_name: str, exit_code: int, detail: str = "") -> str:
    status = "PASS" if exit_code == 0 else "FAIL"
    line = f"[{status}] {display_name} (exit code: {exit_code})"
    if exit_code != 0 and detail.strip():
        return f"{line}\n{detail.strip()}"
    return line


def _run_single(
    script_path: str,
    *,
    headless: bool = False,
) -> tuple[str, int, str]:
    """运行单个脚本，返回 (显示名, 退出码, 详情)。"""
    try:
        res_path = resolve_script_res_path(script_path)
    except (ValueError, FileNotFoundError) as error:
        display_name = script_path
        return display_name, 1, str(error)

    exit_code, combined_output = _execute_test(res_path, headless=headless)
    display_name = res_path.removeprefix("res://")
    detail = combined_output.strip() if exit_code != 0 else ""
    return display_name, exit_code, detail


def run_file(script_path: str, *, headless: bool = False) -> str:
    """运行指定 GD 脚本的 run()，返回汇总信息。"""
    exit_code = prepare_engine()
    if exit_code != 0:
        return f"引擎准备失败 (exit code: {exit_code})"

    display_name, test_exit_code, detail = _run_single(script_path, headless=headless)
    return _format_result(display_name, test_exit_code, detail)


def run_folder(folder_path: str, *, headless: bool = True) -> tuple[bool, str]:
    """并发运行文件夹下全部 .gd 脚本的 run()，返回 (是否全部通过, 汇总信息)。"""
    try:
        script_files = discover_gd_scripts(folder_path)
    except (ValueError, NotADirectoryError) as error:
        return False, str(error)

    if not script_files:
        return True, f"未找到任何 .gd 文件: {folder_path}"

    exit_code = prepare_engine()
    if exit_code != 0:
        return False, f"引擎准备失败 (exit code: {exit_code})"

    results: list[tuple[str, int, str]] = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _run_single,
                script_file.relative_to(PROJECT_ROOT).as_posix(),
                headless=headless,
            ): script_file
            for script_file in script_files
        }
        for future in as_completed(futures):
            results.append(future.result())

    results.sort(key=lambda item: item[0])

    lines: list[str] = []
    for display_name, test_exit_code, detail in results:
        lines.append(_format_result(display_name, test_exit_code, detail))

    total = len(results)
    passed = sum(1 for _, test_exit_code, _ in results if test_exit_code == 0)
    lines.append(f"总计: {total} 测试, {passed} 通过, {total - passed} 失败")

    all_passed = passed == total
    return all_passed, "\n".join(lines)
