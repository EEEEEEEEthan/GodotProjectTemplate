# Godot 自动化测试

## 添加测试

1. 在 `tests/` 目录下创建 `xxx_test.gd`（必须以 `_test.gd` 结尾）
2. 定义一个 `class_name`，实现 `static func run(scene_tree: SceneTree) -> void`
3. 测试通过时调用 `scene_tree.quit(0)`，失败时调用 `scene_tree.quit(1)` 或 `push_error(...)`

无需在其他任何地方注册——测试框架会自动发现。

## 示例

```gdscript
# tests/hello_test.gd
class_name HelloTest
extends RefCounted

static func run(scene_tree: SceneTree) -> void:
	print("hello world")
	scene_tree.quit(0)
```

测试名由文件名推导：`hello_test.gd` → `hello`。

## 运行

```bash
# 运行全部测试
.engine-test-full.bat

# 运行单个测试
powershell -File .engine-test.ps1 -TestName hello
```
