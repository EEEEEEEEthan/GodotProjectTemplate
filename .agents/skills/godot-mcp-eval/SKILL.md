---
name: godot-mcp-eval
description: 通过 Game MCP eval 命令在运行中的 Godot 实例执行 GDScript。需要运行时探查游戏状态、执行诊断脚本、或经 MCP 与运行中游戏交互时使用。
---

# MCP 运行时执行 GDScript

游戏运行后，`McpHandler` 提供 `eval` 命令：编译并执行脚本，调用 `run(scene_tree)` 入口，返回 JSON 可序列化结果。

## 调用方式

优先用 **文件**（`data.file`），不要用内联 `data.source`。

```text
game_command(port=PORT, command="eval", data={"file": "res://path/to/script.gd"})
```

`PORT` 取自游戏启动日志：`Game MCP: HTTP 服务已启动，端口 XXXX`。

## 脚本存放位置

| 场景 | 路径 |
|------|------|
| 临时、一次性探查 | `.temp/xxx.gd` → `res://.temp/xxx.gd` |
| 技能自带、可复用示例 | 技能目录下，如本技能的 `ping.gd` |

`.temp/` 已 gitignore，勿提交临时脚本。

## 脚本约定

完整 GDScript 文件，必须实现：

```gdscript
extends RefCounted

func run(scene_tree: SceneTree) -> Variant:
    # 可用 scene_tree 访问运行中场景树
    return ...  # 返回值会 JSON 序列化；Object 会转成字符串
```

## 示例

本目录 [ping.gd](ping.gd)：

```text
game_command(port=PORT, command="eval", data={"file": "res://.agents/skills/godot-mcp-eval/ping.gd"})
```

预期响应：`{"ok": true, "data": {"result": {"pong": true}}}`

## 注意

- 游戏须已启动且 MCP 插件已启用
- 编译失败或缺少 `run` 时，`data.error` 含错误信息
- `print` 输出在引擎控制台，不在 MCP 响应里
