---
name: egent-test
description: 运行 addons/egent/builtin/test/ 下的自动化测试套件，验证 egent 核心功能。
---

# Egent 测试

运行 `addons/egent/builtin/test/` 目录下的所有 `test_*.py` 测试脚本。

## 运行

```bash
python addons/egent/builtin/skills/egent-test/run.py
```

测试覆盖 egent 核心模块：

- `mcp_bridge` — MCP 桥接生命周期
- `grep_search` — 文件搜索与 ignore 规则
- `file_edit` — 文件编辑权限
- `git` — diff / add / commit
- `pylint` — lint 工具
- `workflow` — 工作流工具
- `delete_file` — 删除文件
- `jason` — jason agent 分析
