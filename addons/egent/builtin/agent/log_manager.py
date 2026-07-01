"""模块级单例日志管理器。

日志文件路径：data_loader.LOG_DIR / YYYYMMDD_HHMMSS.log
使用 atexit 确保进程退出时自动关闭。
"""

from __future__ import annotations

import atexit
import datetime
import os
import typing

import agent.data_loader

_LOG_FILE: typing.TextIO | None = None
_NO_LOG_ENV = "EGENT_NO_LOG"


def _logging_disabled() -> bool:
    return os.environ.get(_NO_LOG_ENV, "").lower() in ("1", "true", "yes")


def write(text: str) -> None:
    """写入日志（首次调用时自动创建日志文件）。"""
    if _logging_disabled():
        return
    global _LOG_FILE  # pylint: disable=global-statement
    if _LOG_FILE is None:
        log_dir = agent.data_loader.LOG_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        _LOG_FILE = open(  # pylint: disable=consider-using-with
            log_dir / f"{timestamp}.log",
            "a",
            encoding="utf-8",
            buffering=1,
        )
        atexit.register(close)
        try:
            log_files = sorted(
                log_dir.glob("*.log"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
            for f in log_files[30:]:
                f.unlink(missing_ok=True)
        except Exception:  # pylint: disable=broad-except
            pass
    _LOG_FILE.write(text)


def flush() -> None:
    """刷新缓冲区。"""
    if _LOG_FILE is not None:
        _LOG_FILE.flush()


def close() -> None:
    """关闭日志文件（idempotent）。"""
    global _LOG_FILE  # pylint: disable=global-statement
    if _LOG_FILE is not None:
        try:
            _LOG_FILE.close()
        finally:
            _LOG_FILE = None
