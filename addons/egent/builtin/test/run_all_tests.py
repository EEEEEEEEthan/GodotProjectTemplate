"""
运行 addons/egent/builtin/test/ 下所有 test_*.py 测试脚本
通过条件：所有测试的退出码都是 0
"""

import pathlib
import subprocess
import sys

TESTS_DIR = pathlib.Path(__file__).resolve().parent
EGENT_ROOT = TESTS_DIR.parent.parent.parent
PROJECT_ROOT = EGENT_ROOT.parent.parent


def run_all(*, verbose: bool = False) -> tuple[bool, str]:
    """运行全部测试，返回 (是否全部通过, 汇总信息)。"""
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    if not test_files:
        message = "未找到任何 test_*.py 测试文件"
        if verbose:
            print(message)
        return True, message

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
            )
            if verbose:
                print(result.stdout)
                if result.stderr:
                    print(f"--- {test_name} stderr ---\n{result.stderr}")
            if result.returncode != 0:
                detail = result.stdout.strip()
                if result.stderr.strip():
                    stderr_text = result.stderr.strip()
                    detail = f"{detail}\n{stderr_text}".strip() if detail else stderr_text
            results.append((test_name, result.returncode, detail))
            if verbose:
                status = "PASS" if result.returncode == 0 else "FAIL"
                print(f"[{status}] {test_name} (exit code: {result.returncode})")
                print()
        except subprocess.TimeoutExpired:
            detail = "超时 180 秒"
            results.append((test_name, -1, detail))
            if verbose:
                print(f"[FAIL] {test_name} ({detail})")
                print()
        except Exception as error:
            detail = f"异常: {error}"
            results.append((test_name, -2, detail))
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


def main() -> int:
    print("=== run_all_tests ===")
    print(f"Tests directory: {TESTS_DIR}")
    print()
    all_pass, _ = run_all(verbose=True)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
