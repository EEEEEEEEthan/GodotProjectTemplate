"""todo_tool 自动化测试。

每个测试在独立的临时目录中运行，确保数据完全隔离。
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tools.todo_tool as todo_tool


class FakeClient:
    """模拟 agent_client，仅提供 name 属性。"""

    def __init__(self, name: str = "test_agent") -> None:
        self.name = name


class TestTodoTool(unittest.TestCase):
    """todo_tool 功能测试。"""

    def setUp(self):
        self.client = FakeClient("test_agent")
        # 每个测试使用独立的临时目录，避免数据泄漏
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp_dir.name)
        # 将 _DATA_DIR 指向临时目录，这样 _TODO_PATH 自然指向临时目录下的 .data/todo.json
        self._orig_data_dir = todo_tool._DATA_DIR
        todo_tool._DATA_DIR = tmp_path
        # 更新 _TODO_PATH 使其指向新 _DATA_DIR
        todo_tool._TODO_PATH = tmp_path / "todo.json"

    def tearDown(self):
        todo_tool._DATA_DIR = self._orig_data_dir
        # 恢复 _TODO_PATH 为基于原 _DATA_DIR 的路径
        todo_tool._TODO_PATH = self._orig_data_dir / "todo.json"
        self._tmp_dir.cleanup()

    # ── add_item ─────────────────────────────────────────

    def test_add_item_normal(self):
        result = todo_tool.add_item(self.client, "修复登录bug", "登录接口返回500")
        self.assertEqual(result, "已添加 todo #1「修复登录bug」")

        # 验证数据已持久化
        data = json.loads(todo_tool._TODO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["next_id"], 2)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], 1)
        self.assertEqual(data["items"][0]["title"], "修复登录bug")
        self.assertEqual(data["items"][0]["content"], "登录接口返回500")
        self.assertIn("created_at", data["items"][0])
        self.assertIn("updated_at", data["items"][0])

    def test_add_item_empty_title(self):
        result = todo_tool.add_item(self.client, "", "some content")
        self.assertEqual(result, "错误：title 不能为空。")

    def test_add_item_blank_title(self):
        result = todo_tool.add_item(self.client, "   ", "some content")
        self.assertEqual(result, "错误：title 不能为空。")

    def test_add_item_empty_content(self):
        result = todo_tool.add_item(self.client, "title", "")
        self.assertEqual(result, "错误：content 不能为空。")

    def test_add_item_blank_content(self):
        result = todo_tool.add_item(self.client, "title", "   ")
        self.assertEqual(result, "错误：content 不能为空。")

    def test_add_item_sequential_ids(self):
        r1 = todo_tool.add_item(self.client, "Task A", "Desc A")
        r2 = todo_tool.add_item(self.client, "Task B", "Desc B")
        r3 = todo_tool.add_item(self.client, "Task C", "Desc C")
        self.assertEqual(r1, "已添加 todo #1「Task A」")
        self.assertEqual(r2, "已添加 todo #2「Task B」")
        self.assertEqual(r3, "已添加 todo #3「Task C」")

    # ── remove_item ──────────────────────────────────────

    def test_remove_item_normal(self):
        todo_tool.add_item(self.client, "Task", "Desc")
        result = todo_tool.remove_item(self.client, 1)
        self.assertEqual(result, "已删除 todo #1「Task」")
        data = json.loads(todo_tool._TODO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), 0)

    def test_remove_item_not_found(self):
        result = todo_tool.remove_item(self.client, 999)
        self.assertEqual(result, "错误：未找到 todo #999")

    # ── update_item ──────────────────────────────────────

    def test_update_item_normal(self):
        todo_tool.add_item(self.client, "Old Title", "Old Content")
        result = todo_tool.update_item(self.client, 1, "New Title", "New Content")
        self.assertEqual(result, "已更新 todo #1「New Title」")
        data = json.loads(todo_tool._TODO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["items"][0]["title"], "New Title")
        self.assertEqual(data["items"][0]["content"], "New Content")

    def test_update_item_empty_title(self):
        todo_tool.add_item(self.client, "Task", "Desc")
        result = todo_tool.update_item(self.client, 1, "", "New Content")
        self.assertEqual(result, "错误：title 不能为空。")

    def test_update_item_empty_content(self):
        todo_tool.add_item(self.client, "Task", "Desc")
        result = todo_tool.update_item(self.client, 1, "New Title", "")
        self.assertEqual(result, "错误：content 不能为空。")

    def test_update_item_not_found(self):
        result = todo_tool.update_item(self.client, 999, "Title", "Content")
        self.assertEqual(result, "错误：未找到 todo #999")

    # ── list_items ───────────────────────────────────────

    def test_list_items_empty(self):
        result = todo_tool.list_items(self.client)
        self.assertEqual(result, "(无待办事项)")

    def test_list_items_with_data(self):
        todo_tool.add_item(self.client, "Task B", "Desc B")
        todo_tool.add_item(self.client, "Task A", "Desc A")
        result = todo_tool.list_items(self.client)
        lines = result.split("\n")
        self.assertEqual(len(lines), 2)
        # 按 id 排序，所以 Task B (id=1) 在前
        self.assertIn("#1", lines[0])
        self.assertIn("Task B", lines[0])
        self.assertIn("#2", lines[1])
        self.assertIn("Task A", lines[1])

    # ── get_item ─────────────────────────────────────────

    def test_get_item_normal(self):
        todo_tool.add_item(self.client, "My Task", "My Content")
        result = todo_tool.get_item(self.client, 1)
        self.assertIn("ID：1", result)
        self.assertIn("标题：My Task", result)
        self.assertIn("正文：My Content", result)
        self.assertIn("创建时间：", result)
        self.assertIn("更新时间：", result)

    def test_get_item_not_found(self):
        result = todo_tool.get_item(self.client, 999)
        self.assertEqual(result, "错误：未找到 todo #999")

    # ── search_items ────────────────────────────────────

    def test_search_items_match_title(self):
        todo_tool.add_item(self.client, "登录bug修复", "修复接口500错误")
        todo_tool.add_item(self.client, "优化性能", "优化数据库查询")
        result = todo_tool.search_items(self.client, "登录")
        lines = result.split("\n")
        self.assertEqual(len(lines), 1)
        self.assertIn("登录bug修复", lines[0])

    def test_search_items_match_content(self):
        todo_tool.add_item(self.client, "任务A", "包含了登录功能")
        result = todo_tool.search_items(self.client, "登录")
        self.assertIn("任务A", result)

    def test_search_items_no_match(self):
        todo_tool.add_item(self.client, "Task", "Desc")
        result = todo_tool.search_items(self.client, "不存在的内容")
        self.assertEqual(result, "(无匹配「不存在的内容」的待办事项)")

    def test_search_items_case_insensitive(self):
        todo_tool.add_item(self.client, "Login Bug", "Fix the login page")
        result = todo_tool.search_items(self.client, "login")
        self.assertIn("Login Bug", result)

    def test_search_items_empty_query(self):
        result = todo_tool.search_items(self.client, "")
        self.assertEqual(result, "错误：query 不能为空。")

    def test_search_items_blank_query(self):
        result = todo_tool.search_items(self.client, "   ")
        self.assertEqual(result, "错误：query 不能为空。")

    # ── 数据持久化 ───────────────────────────────────────

    def test_persistence(self):
        """add 后重新加载应看到数据。"""
        todo_tool.add_item(self.client, "Persist Task", "Persist Content")
        # 模拟重新加载（重新读取文件）
        fresh_data = todo_tool._load_data()
        self.assertEqual(len(fresh_data["items"]), 1)
        self.assertEqual(fresh_data["items"][0]["title"], "Persist Task")

    def test_multiple_ops_integrity(self):
        """连续操作后数据一致性。"""
        todo_tool.add_item(self.client, "A", "Desc A")
        todo_tool.add_item(self.client, "B", "Desc B")
        todo_tool.add_item(self.client, "C", "Desc C")
        todo_tool.remove_item(self.client, 2)
        todo_tool.update_item(self.client, 1, "A Updated", "Desc A Updated")

        data = json.loads(todo_tool._TODO_PATH.read_text(encoding="utf-8"))
        ids = [item["id"] for item in data["items"]]
        self.assertEqual(ids, [1, 3])
        self.assertEqual(data["items"][0]["title"], "A Updated")
        self.assertEqual(data["items"][0]["content"], "Desc A Updated")


if __name__ == "__main__":
    unittest.main()
