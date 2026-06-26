"""运行环境信息查询工具。"""

from __future__ import annotations

import datetime
import locale
import os
import platform
import socket
import sys
import typing

TOOL_SCHEMAS: dict[str, dict[str, typing.Any]] = {
    "system_info_tool_system_info": {
        "type": "function",
        "function": {
            "name": "system_info_tool_system_info",
            "description": "获取当前时间、时区、操作系统与运行环境属性",
            "parameters": {"type": "object", "properties": {}},
        },
    },
}


class SystemInfoTool:
    """获取当前时间、时区、操作系统与运行环境属性。"""

    @staticmethod
    def system_info() -> str:
        """输出全部环境信息。"""
        sections = [
            SystemInfoTool.__format_time(),
            SystemInfoTool.__format_os(),
            SystemInfoTool.__format_env(),
            SystemInfoTool.__format_locale(),
        ]
        return "\n\n".join(section for section in sections if section)

    @staticmethod
    def __format_utc_offset(offset: datetime.timedelta) -> str:
        total_minutes = int(offset.total_seconds() // 60)
        sign = "+" if total_minutes >= 0 else "-"
        total_minutes = abs(total_minutes)
        hours, minutes = divmod(total_minutes, 60)
        return f"UTC{sign}{hours:02d}:{minutes:02d}"

    @staticmethod
    def __format_time() -> str:
        now_local = datetime.datetime.now().astimezone()
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        tz_name = now_local.tzname() or "未知"
        offset_text = SystemInfoTool.__format_utc_offset(
            now_local.utcoffset() or datetime.timedelta()
        )
        lines = [
            "[时间]",
            f"本地时间: {now_local:%Y-%m-%d %H:%M:%S} ({tz_name} {offset_text})",
            f"UTC 时间: {now_utc:%Y-%m-%d %H:%M:%S}",
            f"ISO 本地: {now_local.isoformat(timespec='seconds')}",
            f"ISO UTC: {now_utc:%Y-%m-%dT%H:%M:%SZ}",
            f"星期: {now_local:%A}",
            f"年内第几天: {now_local.timetuple().tm_yday}",
        ]
        return "\n".join(lines)

    @staticmethod
    def __format_os() -> str:
        lines = [
            "[操作系统]",
            f"系统: {platform.system()}",
            f"发行版: {platform.release()}",
            f"版本详情: {platform.version()}",
            f"机器类型: {platform.machine()}",
        ]
        processor = platform.processor()
        if processor:
            lines.append(f"处理器: {processor}")
        lines.append(f"Python: {platform.python_version()} ({sys.executable})")
        return "\n".join(lines)

    @staticmethod
    def __format_env() -> str:
        lines = [
            "[运行环境]",
            f"工作目录: {os.getcwd()}",
            f"用户名: {os.environ.get('USERNAME') or os.environ.get('USER') or '未知'}",
            f"主机名: {socket.gethostname()}",
        ]
        shell = os.environ.get("COMSPEC") or os.environ.get("SHELL")
        if shell:
            lines.append(f"Shell: {shell}")
        return "\n".join(lines)

    @staticmethod
    def __format_locale() -> str:
        lines = ["[区域与编码]"]
        try:
            code, encoding = locale.getlocale()
            lines.append(f"区域: {code or '未知'}")
            lines.append(f"编码: {encoding or '未知'}")
        except locale.Error as error:
            lines.append(f"区域: 无法读取 ({error})")
        try:
            preferred = locale.getpreferredencoding(False)
            lines.append(f"首选编码: {preferred}")
        except Exception as error:  # pylint: disable=broad-exception-caught
            lines.append(f"首选编码: 无法读取 ({error})")
        return "\n".join(lines)
