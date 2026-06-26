"""本地 shell 命令执行工具 — 前台(blocking)与后台(非阻塞)执行。

提供四个工具：
  - shell_tool_exec      : 前台阻塞执行，返回输出
  - shell_tool_bg_exec   : 后台启动进程，立即返回进程 ID 与日志路径
  - shell_tool_bg_status : 查询后台进程状态（运行中/已完成、退出码、输出截断）
  - shell_tool_wait      : 阻塞等待指定秒数
"""

from __future__ import annotations

import datetime
import os
import subprocess
import time
import typing
import uuid

from . import _output_util as output_util

# ---------------------------------------------------------------------------
# 全局后台进程注册表
# ---------------------------------------------------------------------------

_processes: dict[str, dict[str, typing.Any]] = {}


def _read_log_tail(log_path: str, max_lines: int = 50) -> str:
    """读取日志文件尾部内容。"""
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            tail = "".join(lines[-max_lines:])
            return f"(共 {len(lines)} 行，显示末尾 {max_lines} 行)\n...\n{tail}"
        return "".join(lines) if lines else "(空)"
    except FileNotFoundError:
        return "(日志文件未找到)"
    except Exception as e:
        return f"(读取日志失败：{e})"


# ---------------------------------------------------------------------------
# ShellTool — 前台（阻塞）执行
# ---------------------------------------------------------------------------

class ShellTool:
    """执行本地 shell 命令并返回输出。"""

    @staticmethod
    def exec(command: str, cwd: str | None = None) -> str:
        """在本地系统执行任意 shell 命令（cmd /c）。权限极高，无沙箱限制。输出超过 10000 字符会被截断。超时 5 分钟。

        @param command: 要执行的 shell 命令，例如 `dir`、`echo hello`、`python script.py`
        @param cwd: 工作目录，缺省为项目根目录
        """
        if not command or not command.strip():
            return "错误：command 不能为空。"

        work_dir = cwd.strip() if cwd else None
        if work_dir:
            work_dir = os.path.abspath(work_dir)
            if not os.path.isdir(work_dir):
                return f"错误：目录不存在：{work_dir}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=work_dir,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            return "错误：命令执行超时（300 秒）"
        except FileNotFoundError as error:
            return f"错误：命令未找到：{error}"
        except PermissionError as error:
            return f"错误：权限不足：{error}"
        except OSError as error:
            return f"错误：系统调用失败：{error}"

        parts: list[str] = []
        if result.stdout:
            parts.append(result.stdout.strip())
        if result.stderr:
            parts.append(f"[stderr]\n{result.stderr.strip()}")

        output = "\n\n".join(parts) if parts else "(无输出)"
        output = output_util.truncate_output(output)

        if result.returncode != 0:
            output += f"\n\n[exit code: {result.returncode}]"

        return output


# ---------------------------------------------------------------------------
# BgTool — 后台（非阻塞）执行与状态查询
# ---------------------------------------------------------------------------

class BgTool:
    """后台进程管理工具。"""

    # ------------------------------------------------------------------
    # shell_tool_bg_exec
    # ------------------------------------------------------------------
    @staticmethod
    def bg_exec(command: str, cwd: str | None = None) -> str:
        """在后台执行 shell 命令并立即返回。通过返回的 process_id 可用 shell_tool_bg_status 查询执行状态。

        @tool_name shell_tool_bg_exec
        @param command: 要执行的 shell 命令，例如 `dir`、`python train.py`
        @param cwd: 工作目录，缺省为项目根目录
        """
        if not command or not command.strip():
            return "错误：command 不能为空。"

        work_dir = cwd.strip() if cwd else None
        if work_dir:
            work_dir = os.path.abspath(work_dir)
            if not os.path.isdir(work_dir):
                return f"错误：目录不存在：{work_dir}"

        # 生成短唯一 ID
        process_id = uuid.uuid4().hex[:8]

        # 创建日志目录
        log_dir = os.path.join(os.getcwd(), ".egent", ".temp", "bg_logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"bg_{process_id}_{timestamp}.log")

        start_time = time.time()

        # 占位注册（process 字段稍后赋值）
        entry: dict[str, typing.Any] = {
            "command": command,
            "cwd": work_dir,
            "start_time": start_time,
            "end_time": None,
            "returncode": None,
            "log_path": log_path,
            "finished": False,
            "process": None,
            "log_file": None,
        }
        _processes[process_id] = entry

        # 后台启动进程
        try:
            log_file = open(log_path, "w", encoding="utf-8")
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=work_dir,
            )
            entry["process"] = process
            entry["log_file"] = log_file
        except Exception as e:
            entry["finished"] = True
            entry["returncode"] = -1
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write(f"启动失败：{e}\n")
            except Exception:
                pass
            return (
                f"错误：启动进程失败：{e}\n"
                f"ID：{process_id}\n"
                f"日志路径：{log_path}"
            )

        return (
            f"进程已后台启动。\n"
            f"ID：{process_id}\n"
            f"日志路径：{log_path}\n"
            f"命令：{command}\n"
            f"\n"
            f"使用 shell_tool_bg_status 查询状态：\n"
            f'  process_id="{process_id}"'
        )

    # ------------------------------------------------------------------
    # shell_tool_bg_status
    # ------------------------------------------------------------------
    @staticmethod
    def bg_status(process_id: str) -> str:
        """查询后台进程的执行状态。返回是否完成、退出码、已运行时间与最新日志输出。

        @tool_name shell_tool_bg_status
        @param process_id: shell_tool_bg_exec 返回的进程 ID
        """
        if process_id not in _processes:
            return f"错误：未找到进程 ID：{process_id}"

        entry = _processes[process_id]
        process: subprocess.Popen | None = entry.get("process")
        elapsed = time.time() - entry["start_time"]

        if process is not None and not entry["finished"]:
            ret = process.poll()
            if ret is not None:
                entry["finished"] = True
                entry["returncode"] = ret
                entry["end_time"] = time.time()
                lf = entry.get("log_file")
                if lf is not None:
                    try:
                        lf.close()
                    except Exception:
                        pass
                    entry["log_file"] = None

        finished = entry["finished"]
        returncode = entry["returncode"]
        log_path = entry["log_path"]

        log_tail = _read_log_tail(log_path)
        log_tail = output_util.truncate_output(log_tail)

        if finished:
            if returncode == 0:
                status = "✅ 已完成"
            elif returncode == -1:
                status = "❌ 启动失败"
            else:
                status = f"⚠️ 已结束（exit code: {returncode}）"
        else:
            status = "🔄 运行中"

        run_time = f"{elapsed:.1f} 秒"
        if entry["end_time"]:
            run_time += f"（总耗时：{entry['end_time'] - entry['start_time']:.1f} 秒）"

        return (
            f"进程 ID：{process_id}\n"
            f"状态：{status}\n"
            f"运行时间：{run_time}\n"
            f"日志路径：{log_path}\n"
            f"--- 最新日志输出 ---\n{log_tail}"
        )

    # ------------------------------------------------------------------
    # shell_tool_wait
    # ------------------------------------------------------------------
    @staticmethod
    def wait(seconds: float) -> str:
        """等待指定的秒数（最长 120 秒）。用于需要延时的场景，如等待游戏启动、等待文件生成。

        @tool_name shell_tool_wait
        @param seconds: 等待的秒数（0.1 ~ 120）
        """
        if seconds <= 0:
            return "已等待 0 秒。"
        if seconds > 120:
            return "错误：等待时间不能超过 120 秒。"

        time.sleep(seconds)
        return f"已等待 {seconds} 秒。"
