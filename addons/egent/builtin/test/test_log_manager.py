"""测试 log_manager 日志清理机制。"""

from __future__ import annotations

import datetime
import os
import pathlib
import sys
import tempfile

from _test_setup import *  # noqa: F401

import agent.data_loader
import agent.log_manager


def _touch_log_file(
    dir_path: pathlib.Path,
    name: str,
    *,
    days_ago: int,
) -> pathlib.Path:
    """在 dir_path 下创建 .log 文件，将修改时间设为 days_ago 天前。"""
    file_path = dir_path / name
    file_path.write_text("")
    ts = (datetime.datetime.now() - datetime.timedelta(days=days_ago)).timestamp()
    os.utime(file_path, (ts, ts))
    return file_path


def test_log_cleanup_keeps_latest_30() -> None:
    """创建 35 个旧日志文件，触发 write() 后应只保留 30 个。"""
    # 保存原始状态
    orig_no_log = os.environ.pop("EGENT_NO_LOG", None)
    orig_log_dir = agent.data_loader.LOG_DIR
    orig_log_file = agent.log_manager._LOG_FILE

    try:
        # 重置模块状态以便 write() 创建新文件
        agent.log_manager._LOG_FILE = None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = pathlib.Path(tmpdir)
            agent.data_loader.LOG_DIR = tmp_path

            # 创建 35 个旧日志文件，mtime 分布在 30~64 天前
            for i in range(35):
                _touch_log_file(tmp_path, f"old_{i:03d}.log", days_ago=30 + i)

            # 触发 write() —— 创建新日志文件并清理旧文件
            agent.log_manager.write("test payload")

            # 清理后目录中文件数 = 保留的旧文件 + 新创建的文件
            remaining = sorted(tmp_path.glob("*.log"))
            # 35 旧 + 1 新 = 36 个文件，保留最新 30 个，删除最旧 6 个 → 30 个
            assert len(remaining) == 30, (
                f"期望保留 30 个日志文件，实际 {len(remaining)}"
            )

            # 验证最旧的 6 个文件（old_029~old_034）已被删除
            basenames = {f.name for f in remaining}
            for i in range(29, 35):
                assert f"old_{i:03d}.log" not in basenames, (
                    f"最旧文件 old_{i:03d}.log 应该被删除"
                )

            # 验证新创建的日志文件存在
            has_new = any(f.name != "new.log" and f.name.startswith("20") for f in remaining)
            assert has_new, "新创建的日志文件应该存在"

            agent.log_manager.flush()
            agent.log_manager.close()

    finally:
        # 恢复原始状态
        if orig_no_log is None:
            os.environ.pop("EGENT_NO_LOG", None)
        else:
            os.environ["EGENT_NO_LOG"] = orig_no_log
        agent.data_loader.LOG_DIR = orig_log_dir
        agent.log_manager._LOG_FILE = orig_log_file


def main() -> int:
    test_log_cleanup_keeps_latest_30()
    print("PASS test_log_manager")
    return 0


if __name__ == "__main__":
    sys.exit(main())
