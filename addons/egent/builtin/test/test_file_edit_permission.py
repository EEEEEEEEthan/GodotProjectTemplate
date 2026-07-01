"""测试 file_edit_tool 的写权限系统（_resolve_writable_file 三层检查）。"""

from __future__ import annotations

import os
import pathlib
import tempfile

from _test_setup import *  # noqa: F401

import agent.tool_binding as tool_binding
import tools.file_edit_tool
from agent.agent_config import AgentConfig


class MockAgent:
    def __init__(self, no_write_files=None):
        self.config = AgentConfig()
        if no_write_files is not None:
            self.config.no_write_files = list(no_write_files)
        self.name = "test"


def _wrap(agent, fn):
    return tool_binding.wrap_tool(agent, fn)


# ── L1: 路径合法性 ──────────────────────────────────────────────

def test_l1_empty_path():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)
    delete = _wrap(agent, tools.file_edit_tool.delete_file)
    patch = _wrap(agent, tools.file_edit_tool.apply_patch)

    assert "不能为空" in create(file_path="")
    assert "不能为空" in delete(file_path="")
    assert "不能为空" in patch(file_path="", old_text="x")


def test_l1_absolute_path():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)

    # 使用平台相关的绝对路径
    abs_path = str(pathlib.Path(tempfile.gettempdir()) / "test_abs.py")
    result = create(file_path=abs_path)
    assert "不接受绝对路径" in result


# ── L2: 写黑名单 ────────────────────────────────────────────────

def test_l2_no_write_egent():
    """禁止写 addons/egent 目录下的文件。"""
    agent = MockAgent(no_write_files=["addons/egent"])
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            os.makedirs("addons/egent", exist_ok=True)
            result = create(file_path="addons/egent/something.py", content="bad")
            assert result == "错误：你无权修改这些文件：addons/egent"
        finally:
            os.chdir(original_cwd)


def test_l2_no_write_pyc():
    """禁止写 *.pyc 文件。"""
    agent = MockAgent(no_write_files=["*.pyc"])
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = create(file_path="mymodule.cpython-311.pyc")
            assert result == "错误：你无权修改这些文件：*.pyc"
        finally:
            os.chdir(original_cwd)


def test_l2_no_write_in_subdir():
    """写黑名单检查路径的每个段。"""
    agent = MockAgent(no_write_files=["addons/egent"])
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            os.makedirs("foo/addons/egent/bar", exist_ok=True)
            result = create(file_path="foo/addons/egent/bar/test.py")
            assert result == "错误：你无权修改这些文件：addons/egent"
        finally:
            os.chdir(original_cwd)


# ── L3: 存在性检查 ──────────────────────────────────────────────

def test_l3_create_must_not_exist():
    """create 时文件不能已存在。"""
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            # 先创建
            create(file_path="existing.txt")
            # 再创建同名
            result = create(file_path="existing.txt")
            assert "已存在" in result
        finally:
            os.chdir(original_cwd)


def test_l3_delete_must_exist():
    """delete 时文件必须存在。"""
    agent = MockAgent()
    delete = _wrap(agent, tools.file_edit_tool.delete_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = delete(file_path="nonexistent.txt")
            assert "不存在" in result
        finally:
            os.chdir(original_cwd)


def test_l3_patch_must_exist():
    """patch 时文件必须存在。"""
    agent = MockAgent()
    patch = _wrap(agent, tools.file_edit_tool.apply_patch)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = patch(file_path="nonexistent.txt", old_text="hello")
            assert "不存在" in result
        finally:
            os.chdir(original_cwd)


# ── 正常流程 ────────────────────────────────────────────────────

def test_create_file_success():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = create(file_path="hello.txt", content="world")
            assert result == "成功"
            with open("hello.txt", encoding="utf-8") as f:
                assert f.read() == "world"
        finally:
            os.chdir(original_cwd)


def test_create_file_nested_dirs():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = create(file_path="a/b/c/test.txt", content="deep")
            assert result == "成功"
            assert os.path.isfile("a/b/c/test.txt")
        finally:
            os.chdir(original_cwd)


def test_delete_file_success():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)
    delete = _wrap(agent, tools.file_edit_tool.delete_file)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            create(file_path="todelete.txt")
            result = delete(file_path="todelete.txt")
            assert result == "成功"
            assert not os.path.exists("todelete.txt")
        finally:
            os.chdir(original_cwd)


def test_apply_patch_success():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)
    patch = _wrap(agent, tools.file_edit_tool.apply_patch)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            create(file_path="code.py", content="x = 1\ny = 2\nz = 3\n")
            result = patch(file_path="code.py", old_text="y = 2", new_text="y = 42")
            assert result == "成功"
            with open("code.py", encoding="utf-8") as f:
                assert f.read() == "x = 1\ny = 42\nz = 3\n"
        finally:
            os.chdir(original_cwd)


# ── apply_patch 拒绝绝对路径 ────────────────────────────────────

def test_apply_patch_rejects_absolute_path():
    agent = MockAgent()
    patch = _wrap(agent, tools.file_edit_tool.apply_patch)

    abs_path = str(pathlib.Path(tempfile.gettempdir()) / "test_patch_abs.py")
    result = patch(file_path=abs_path, old_text="hello")
    assert "不接受绝对路径" in result


def test_apply_patch_empty_old_text():
    agent = MockAgent()
    create = _wrap(agent, tools.file_edit_tool.create_file)
    patch = _wrap(agent, tools.file_edit_tool.apply_patch)

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            create(file_path="test.txt", content="hello")
            result = patch(file_path="test.txt", old_text="")
            assert "不能为空" in result
        finally:
            os.chdir(original_cwd)


# ── 主入口 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    test_l1_empty_path()
    test_l1_absolute_path()
    test_l2_no_write_egent()
    test_l2_no_write_pyc()
    test_l2_no_write_in_subdir()
    test_l3_create_must_not_exist()
    test_l3_delete_must_exist()
    test_l3_patch_must_exist()
    test_create_file_success()
    test_create_file_nested_dirs()
    test_delete_file_success()
    test_apply_patch_success()
    test_apply_patch_rejects_absolute_path()
    test_apply_patch_empty_old_text()
    print("✅ file_edit_tool 写权限测试全部通过")
