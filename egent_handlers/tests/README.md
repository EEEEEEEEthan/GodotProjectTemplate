# Godot 回归测试

项目级回归测试，通过 Godot 引擎 headless/有窗口运行，验证游戏逻辑与场景行为。

- 测试用例：`egent_handlers/tests/*_test.gd`
- 分发入口：`addons/egent/godot_test_runner.gd`
- 运行器：`addons/egent/godot_test.py`（由 `egent.bat --test` 调用）

## 添加测试

1. 在 `egent_handlers/tests/` 下创建 `xxx_test.gd`（建议以 `_test.gd` 结尾）
2. 定义 `class_name`，实现 `static func run(scene_tree: SceneTree) -> void`
3. 通过时 `scene_tree.quit(0)`，失败时 `scene_tree.quit(1)` 或 `push_error(...)`

放入该目录的 `.gd` 文件会被 `--test-folder` 自动发现，无需手动注册。

## 示例

```gdscript
# egent_handlers/tests/hello_test.gd
class_name HelloTest
extends RefCounted

static func run(scene_tree: SceneTree) -> void:
	print("hello world")
	scene_tree.quit(0)
```

## 运行

```bash
# 单个回归测试（相对路径或 res:// 均可）
egent.bat --test egent_handlers/tests/hello_test.gd

# 无头模式（CI / 无 GPU 环境）
egent.bat --test egent_handlers/tests/hello_test.gd --headless

# 全量回归（自动发现目录下全部 .gd）
egent.bat --test-folder egent_handlers/tests
egent.bat --test-folder egent_handlers/tests --headless
```
