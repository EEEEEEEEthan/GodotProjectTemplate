"""godot-shell: 在 Agent 工作目录下执行任意系统命令。

用法：
    python exec.py <命令>
    python exec.py <命令参数...>

将全部参数拼接后通过系统 Shell 执行，返回 stdout+stderr 合并输出。
"""

import subprocess
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("错误：请提供要执行的命令。")
        print("用法：exec.py <命令及其参数>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 分钟超时，防止挂起
        )
    except subprocess.TimeoutExpired:
        print("错误：命令执行超时（300 秒）")
        sys.exit(1)
    except OSError as e:
        print(f"错误：无法执行命令 — {e}")
        sys.exit(1)

    output = completed.stdout + completed.stderr
    if completed.returncode != 0:
        print(f"[退出码: {completed.returncode}]")
    print(output if output else "(无输出)")


if __name__ == "__main__":
    main()
