# Godot 回归测试

项目级回归测试，通过 Godot 引擎 headless/有窗口运行，验证游戏逻辑与场景行为。

- 测试用例：`egent_handlers/tests/*_test.gd`
- 分发入口：`addons/egent/test.gd`
- 运行器：`addons/egent/godot_test.py`（由 `egent.bat --test` 调用）

## 添加测试

1. 在 `egent_handlers/tests/` 下创建 `xxx_test.gd`（必须以 `_test.gd` 结尾）
2. 定义 `class_name`，实现 `static func run(scene_tree: SceneTree) -> void`
3. 通过时 `scene_tree.quit(0)`，失败时 `scene_tree.quit(1)` 或 `push_error(...)`

无需注册，框架按文件名自动发现。

## 示例

```gdscript
# egent_handlers/tests/hello_test.gd
class_name HelloTest
extends RefCounted

static func run(scene_tree: SceneTree) -> void:
	print("hello world")
	scene_tree.quit(0)
```

测试名由文件名推导：`hello_test.gd` → `hello`。

## 运行

```bash
# 全部回归测试
egent.bat --test all

# 单个回归测试
egent.bat --test hello

# 无头模式（CI / 无 GPU 环境）
egent.bat --test all --headless
egent.bat --test hello --headless
```

兼容旧入口（内部均委托 `egent.bat --test`）：

```bash
.engine-test-full.bat
.engine-test-full.bat --headless
powershell -File .engine-test.ps1 hello
powershell -File .engine-test.ps1 hello -Headless
```
