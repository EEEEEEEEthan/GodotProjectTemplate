---
name: godot-shell
description: 通过技能脚本在 Agent 工作目录下执行任意系统 Shell 命令。仅限 ethan 自用，权限极高，慎用。
---

# godot-shell — 系统命令执行技能

> ⚠ **仅限 ethan 自用。** 此技能可直接执行任意系统命令，无沙箱限制。

## 用法

调用技能脚本 `exec.py`，将待执行命令作为参数传入：

```text
skill_tool_run_skill_script(
    skill_id="godot-shell",
    relative_path="exec.py",
    script_args=["你的命令"]
)
```

### 示例

```text
skill_tool_run_skill_script(
    skill_id="godot-shell",
    relative_path="exec.py",
    script_args=["dir"]
)
```

```text
skill_tool_run_skill_script(
    skill_id="godot-shell",
    relative_path="exec.py",
    script_args=["powershell -Command Get-Process"]
)
```

```text
skill_tool_run_skill_script(
    skill_id="godot-shell",
    relative_path="exec.py",
    script_args=["python --version"]
)
```

## 注意事项

- 命令在 Agent 当前工作目录下执行
- 标准输出与标准错误合并返回
- 输出超过 10,000 字符会自动截断保存
- 谨慎使用删除、写入、网络请求等高危操作
- 此技能不会在系统消息中列出给其他 agent，仅 ethan 知晓
