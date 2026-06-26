"""
运行 .ethan/test/ 下所有 test_*.py 测试脚本
通过条件：所有测试的退出码都是 0
"""

import pathlib
import subprocess
import sys

TESTS_DIR = pathlib.Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent.parent  # .ethan/test -> .ethan -> 根目录


def main() -> int:
    print("=== run_all_tests ===")
    print(f"Tests directory: {TESTS_DIR}")
    print()

    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    if not test_files:
        print("未找到任何 test_*.py 测试文件")
        return 0

    results: list[tuple[str, int]] = []
    for test_file in test_files:
        test_name = test_file.name
        print(f"[RUN] {test_name}")
        try:
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
                encoding="utf-8",
            )
            print(result.stdout)
            if result.stderr:
                print(f"--- {test_name} stderr ---\n{result.stderr}")
            results.append((test_name, result.returncode))
            status = "PASS" if result.returncode == 0 else "FAIL"
            print(f"[{status}] {test_name} (exit code: {result.returncode})")
        except subprocess.TimeoutExpired:
            print(f"[FAIL] {test_name} (超时 180 秒)")
            results.append((test_name, -1))
        except Exception as e:
            print(f"[FAIL] {test_name} (异常: {e})")
            results.append((test_name, -2))
        print()

    print("=== 汇总 ===")
    all_pass = True
    for name, code in results:
        status = "PASS" if code == 0 else "FAIL"
        all_pass = all_pass and (code == 0)
        print(f"  [{status}] {name} (exit code: {code})")

    total = len(results)
    passed = sum(1 for _, c in results if c == 0)
    print(f"\n总计: {total} 测试, {passed} 通过, {total - passed} 失败")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
