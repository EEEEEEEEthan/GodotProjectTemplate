"""
测试：以根目录为工作目录，让 jason 分析工程
通过条件：看到任何成功的工具调用（格式如 [tool_name] ...）
退出码 0 表示通过
"""

import re
import subprocess
import sys

PROJECT_ROOT = r"C:\Projects\Template"
PROMPT = "请分析这个工程，用 walk_files 看看项目结构，然后总结一下这是个什么项目"


def main() -> int:
    print(f"=== test_jason_analyze ===")
    print(f"Working directory: {PROJECT_ROOT}")

    cmd = [sys.executable, ".ethan/main.py", "jason"]

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            input=PROMPT,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        print("FAILED: jason 运行超时（120 秒）")
        return 1
    except FileNotFoundError as e:
        print(f"FAILED: 无法找到可执行文件: {e}")
        return 1
    except Exception as e:
        print(f"FAILED: 运行 jason 时出现异常: {e}")
        return 1

    combined = result.stdout + result.stderr
    print(f"\n--- jason stdout ---\n{result.stdout}")
    if result.stderr:
        print(f"\n--- jason stderr ---\n{result.stderr}")

    # 检测工具调用：格式为 [tool_name] 或 [tool_name] 参数
    # 例如: [walk_files_tool_walk_files] directory=., depth=3
    tool_call_pattern = re.compile(r"\[[\w-]+\]")
    tool_calls = tool_call_pattern.findall(combined)

    if tool_calls:
        print(f"\nPASS: jason 成功发起了工具调用 ({len(tool_calls)} 次)")
        for tc in tool_calls:
            print(f"  - {tc}")
        return 0
    else:
        print("\nFAIL: 未检测到任何工具调用")
        return 1


if __name__ == "__main__":
    sys.exit(main())
