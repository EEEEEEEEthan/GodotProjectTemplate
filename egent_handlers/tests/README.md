# Godot 回归测试

项目级回归测试，通过 Godot 引擎 headless/有窗口运行，验证游戏逻辑与场景行为。

- 测试用例：`egent_handlers/tests/*_test.gd`
- 分发入口：`addons/egent/godot_test_runner.gd`
- 运行器：`addons/egent/godot_test.py`（由 `egent.bat --test` 调用）

## 添加测试

1. 在 `egent_handlers/tests/` 下创建 `xxx_test.gd`（建议以 `_test.gd` 结尾）
2. 定义 `class_name`，实现 `static func run(scene_tree: SceneTree) -> void`
3. 通过时 `scene_tree.quit(0)`，失败时 `scene_tree.quit(1)` 或 `push_error(...)`
4. 全量列表：在 `.engine-test-full.bat` 的 `for %%t in (...)` 中追加脚本路径

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
```

兼容旧入口（内部均委托 `egent.bat --test`）：

```bash
.engine-test-full.bat
.engine-test-full.bat --headless
powershell -File .engine-test.ps1 egent_handlers/tests/hello_test.gd
powershell -File .engine-test.ps1 egent_handlers/tests/hello_test.gd -Headless
```
