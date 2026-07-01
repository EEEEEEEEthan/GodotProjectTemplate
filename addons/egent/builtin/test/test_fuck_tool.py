"""fuck_tool 自动化测试。

每个测试在独立的临时目录中运行，确保数据完全隔离。
"""

from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from _test_setup import *  # noqa: F401

import tools.fuck_tool as fuck_tool


class FakeClient:
    """模拟 agent_client，仅提供 name 属性。"""

    def __init__(self, name: str = "test_agent") -> None:
        self.name = name


class TestFuckTool(unittest.TestCase):
    """fuck_tool 功能测试。"""

    def setUp(self):
        self.client = FakeClient("test_agent")
        self._tmp_dir = tempfile.TemporaryDirectory()
        tmp_path = pathlib.Path(self._tmp_dir.name)
        self._orig_data_dir = fuck_tool._DATA_DIR
        fuck_tool._DATA_DIR = tmp_path
        fuck_tool._FUCK_PATH = tmp_path / "fuck.json"

    def tearDown(self):
        fuck_tool._DATA_DIR = self._orig_data_dir
        fuck_tool._FUCK_PATH = self._orig_data_dir / "fuck.json"
        self._tmp_dir.cleanup()

    # ── fuck ──────────────────────────────────────────────

    def test_fuck_normal(self):
        result = fuck_tool.fuck(self.client, "这代码真烂")
        self.assertIn("😤 **收到！**", result)
        self.assertIn("#1 这代码真烂", result)

        data = json.loads(fuck_tool._FUCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["next_id"], 2)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["id"], 1)
        self.assertEqual(data["items"][0]["complaint"], "这代码真烂")
        self.assertEqual(data["items"][0]["author"], "test_agent")
        self.assertIn("created_at", data["items"][0])

    def test_fuck_empty_complaint(self):
        result = fuck_tool.fuck(self.client, "")
        self.assertEqual(result, "错误：complaint 不能为空。")

    def test_fuck_blank_complaint(self):
        result = fuck_tool.fuck(self.client, "   ")
        self.assertEqual(result, "错误：complaint 不能为空。")

    def test_fuck_sequential_ids(self):
        r1 = fuck_tool.fuck(self.client, "A")
        r2 = fuck_tool.fuck(self.client, "B")
        r3 = fuck_tool.fuck(self.client, "C")
        self.assertIn("#1 A", r1)
        self.assertIn("#2 B", r2)
        self.assertIn("#3 C", r3)

    # ── remove ────────────────────────────────────────────

    def test_remove_normal(self):
        fuck_tool.fuck(self.client, "Task")
        result = fuck_tool.remove( 1)
        self.assertIn("已删除 fuck #1", result)
        data = json.loads(fuck_tool._FUCK_PATH.read_text(encoding="utf-8"))
        self.assertEqual(len(data["items"]), 0)

    def test_remove_not_found(self):
        result = fuck_tool.remove( 999)
        self.assertEqual(result, "错误：未找到 fuck #999")

    # ── list_items ────────────────────────────────────────

    def test_list_items_empty(self):
        result = fuck_tool.list_items()
        self.assertEqual(result, "(无 fuck 条目)")

    def test_list_items_with_data(self):
        fuck_tool.fuck(self.client, "B first")
        fuck_tool.fuck(self.client, "A second")
        result = fuck_tool.list_items()
        lines = result.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("#1", lines[0])
        self.assertIn("B first", lines[0])
        self.assertIn("[test_agent]", lines[0])
        self.assertIn("#2", lines[1])
        self.assertIn("A second", lines[1])
        self.assertIn("[test_agent]", lines[1])

    # ── get ───────────────────────────────────────────────

    def test_get_normal(self):
        fuck_tool.fuck(self.client, "My complaint")
        result = fuck_tool.get( 1)
        self.assertIn("ID：1", result)
        self.assertIn("作者：test_agent", result)
        self.assertIn("吐槽：My complaint", result)
        self.assertIn("创建时间：", result)

    def test_get_not_found(self):
        result = fuck_tool.get( 999)
        self.assertEqual(result, "错误：未找到 fuck #999")

    # ── search ────────────────────────────────────────────

    def test_search_match_complaint(self):
        fuck_tool.fuck(self.client, "登录bug修复")
        fuck_tool.fuck(self.client, "优化性能")
        result = fuck_tool.search( "登录")
        lines = result.split("\n")
        self.assertEqual(len(lines), 1)
        self.assertIn("登录bug修复", lines[0])

    def test_search_match_complaint_exact(self):
        fuck_tool.fuck(self.client, "随便说点啥")
        result = fuck_tool.search( "随便说点啥")
        self.assertIn("随便说点啥", result)

    def test_search_no_match(self):
        fuck_tool.fuck(self.client, "Task")
        result = fuck_tool.search( "不存在")
        self.assertEqual(result, "(无匹配「不存在」的 fuck 条目)")

    def test_search_case_insensitive(self):
        fuck_tool.fuck(self.client, "Login Bug")
        result = fuck_tool.search( "login")
        self.assertIn("Login Bug", result)

    def test_search_empty_query(self):
        result = fuck_tool.search( "")
        self.assertEqual(result, "错误：query 不能为空。")

    def test_search_blank_query(self):
        result = fuck_tool.search( "   ")
        self.assertEqual(result, "错误：query 不能为空。")

    # ── add_comment ─────────────────────────────────────────

    def test_add_comment_normal(self):
        fuck_tool.fuck(self.client, "这代码真烂")
        result = fuck_tool.add_comment(self.client, 1, "确实，我也看不下去了")
        self.assertEqual(result, "💬 已评论 fuck #1")

        data = json.loads(fuck_tool._FUCK_PATH.read_text(encoding="utf-8"))
        item = data["items"][0]
        self.assertEqual(len(item["comments"]), 1)
        comment = item["comments"][0]
        self.assertEqual(comment["comment"], "确实，我也看不下去了")
        self.assertEqual(comment["author"], "test_agent")
        self.assertIn("created_at", comment)

    def test_add_comment_empty(self):
        fuck_tool.fuck(self.client, "吐槽一下")
        result = fuck_tool.add_comment(self.client, 1, "")
        self.assertEqual(result, "错误：comment 不能为空。")

    def test_add_comment_blank(self):
        fuck_tool.fuck(self.client, "吐槽一下")
        result = fuck_tool.add_comment(self.client, 1, "   ")
        self.assertEqual(result, "错误：comment 不能为空。")

    def test_add_comment_not_found(self):
        result = fuck_tool.add_comment(self.client, 999, "不存在的条目")
        self.assertEqual(result, "错误：未找到 fuck #999")

    def test_add_comment_multiple(self):
        fuck_tool.fuck(self.client, "多评论测试")
        fuck_tool.add_comment(self.client, 1, "第一条评论")
        fuck_tool.add_comment(self.client, 1, "第二条评论")
        fuck_tool.add_comment(self.client, 1, "第三条评论")

        data = json.loads(fuck_tool._FUCK_PATH.read_text(encoding="utf-8"))
        comments = data["items"][0]["comments"]
        self.assertEqual(len(comments), 3)
        self.assertEqual(comments[0]["comment"], "第一条评论")
        self.assertEqual(comments[1]["comment"], "第二条评论")
        self.assertEqual(comments[2]["comment"], "第三条评论")

    # ── get 含评论 ────────────────────────────────────────

    def test_get_with_comments(self):
        fuck_tool.fuck(self.client, "带评论的吐槽")
        fuck_tool.add_comment(self.client, 1, "评论A")
        fuck_tool.add_comment(self.client, 1, "评论B")
        result = fuck_tool.get( 1)
        self.assertIn("评论 #1", result)
        self.assertIn("评论A", result)
        self.assertIn("评论 #2", result)
        self.assertIn("评论B", result)

    def test_get_no_comments(self):
        fuck_tool.fuck(self.client, "无评论的吐槽")
        result = fuck_tool.get( 1)
        self.assertIn("(无评论)", result)

    # ── 数据持久化 ───────────────────────────────────────

    def test_persistence(self):
        fuck_tool.fuck(self.client, "Persist complaint")
        fresh_data = fuck_tool._load_data()
        self.assertEqual(len(fresh_data["items"]), 1)
        self.assertEqual(fresh_data["items"][0]["complaint"], "Persist complaint")

    def test_multiple_ops_integrity(self):
        fuck_tool.fuck(self.client, "A")
        fuck_tool.fuck(self.client, "B")
        fuck_tool.fuck(self.client, "C")
        fuck_tool.remove( 2)

        data = json.loads(fuck_tool._FUCK_PATH.read_text(encoding="utf-8"))
        ids = [item["id"] for item in data["items"]]
        self.assertEqual(ids, [1, 3])


if __name__ == "__main__":
    unittest.main()
