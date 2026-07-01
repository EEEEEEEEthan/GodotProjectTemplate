"""
运行 addons/egent/builtin/test/ 下所有 test_*.py 测试脚本
通过条件：所有测试的退出码都是 0
"""

import os
import pathlib
import subprocess
import sys

TESTS_DIR = pathlib.Path(__file__).resolve().parent
EGENT_ROOT = TESTS_DIR.parent.parent
PROJECT_ROOT = EGENT_ROOT.parent.parent
BUILTIN_DIR = EGENT_ROOT / "builtin"


def _env_with_pythonpath() -> dict[str, str]:
    """返回追加了 PYTHONPATH 的环境变量副本。"""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    paths = [p for p in existing.split(os.pathsep) if p] if existing else []
    builtin_str = str(BUILTIN_DIR)
    if builtin_str not in paths:
        paths.insert(0, builtin_str)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env


def run_all(*, verbose: bool = False) -> tuple[bool, str]:
    """运行全部测试，返回 (是否全部通过, 汇总信息)。"""
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    if not test_files:
        return True, "⚠️ 未找到测试文件"

    results: list[tuple[str, int, str]] = []
    for test_file in test_files:
        test_name = test_file.name
        if verbose:
            print(f"[RUN] {test_name}")
        detail = ""
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
                env=_env_with_pythonpath(),
            )
            if verbose:
                stdout = result.stdout.strip()
                stderr = result.stderr.strip()
                if stdout or stderr:
                    print(stdout)
                    if stderr:
                        print(stderr)
            summary_lines = []
            if result.stdout.strip():
                summary_lines.append(result.stdout.strip())
            if result.stderr.strip():
                summary_lines.append(result.stderr.strip())
            detail = "\n".join(summary_lines)
            results.append((test_name, result.returncode, detail))
        except subprocess.TimeoutExpired:
            results.append((test_name, -1, "[timeout]"))

    passed = [n for n, c, _ in results if c == 0]
    failed = [(n, c, d) for n, c, d in results if c != 0]

    lines: list[str] = []
    for name, code, detail in results:
        if code == 0:
            lines.append(f"[PASS] {name} (exit code: 0)")
        else:
            lines.append(f"[FAIL] {name} (exit code: {code})")
            if detail:
                lines.append(detail)

    summary = "\n".join(lines)
    total = len(results)
    summary += f"\n总计: {total} 测试, {len(passed)} 通过, {len(failed)} 失败"
    return len(failed) == 0, summary


if __name__ == "__main__":
    all_pass, summary = run_all(verbose=True)
    print(summary)
    sys.exit(0 if all_pass else 1)
