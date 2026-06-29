---
name: egent-test
description: 运行 .egent/builtin/test/ 下的自动化测试套件，验证 .egent 核心功能。
---

# 测试技能

## 概述
运行 `.egent/builtin/test/` 目录下的所有 `test_*.py` 测试脚本。

## 使用方式
调用 `run.py` 脚本即可运行全部测试：

```
python .egent/builtin/skills/egent-test/run.py
```

## 测试内容
测试覆盖 .egent 核心模块：
- agent_client 功能
- tool_binding 工具绑定
- grep_search 搜索工具
- pylint_tool 代码检查
- workflow_tool 工作流工具
- context_trim 上下文裁剪
- jason_analyze 分析功能
- mcp_bridge MCP 桥接生命周期与关闭容错

## 注意事项
- 测试从项目根目录运行
- 所有测试必须通过（退出码 0）
- 测试超时时间 180 秒
