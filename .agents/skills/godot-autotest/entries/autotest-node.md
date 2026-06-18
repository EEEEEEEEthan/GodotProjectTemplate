# Test 分发器

## 职责

`tests/test.gd`（`class_name Test`，`extends SceneTree`）作为 `--script` 入口，负责：

1. 从命令行读取 `--autotest` 后的 `TESTNAME`
2. 在 `run_named` 中 match 分发到对应测试类
3. 测试类接收 `SceneTree` 引用，结束时调用 `scene_tree.quit(exit_code)`

主场景不参与 autotest；正常启动与测试启动完全分离。

## 命令行解析

启动格式：`--script res://tests/test.gd [--headless] -- --autotest TESTNAME`（`--` 后为 Godot 用户参数）。

使用 `OS.get_cmdline_user_args()` 扫描 `--autotest`，下一项即为 `TESTNAME`。

## 注册与分发

在 `run_named` 的 `match` 中注册 `TESTNAME`。每个测试类放在 `tests/`，`extends RefCounted`，实现 `static func run(scene_tree: SceneTree) -> void`。

```gdscript
func run_named(test_name: String) -> void:
	match test_name:
		"hellotest":
			HelloTest.run(self)
			return
	push_error("'%s' not found" % test_name)
	quit(1)
```

## 退出码

| 结果 | `quit` |
|------|--------|
| 通过 | `0` |
| 断言/逻辑失败 | `1`（或约定非零码） |
| 未知测试名 | `1` |

`.engine-test.ps1` 将引擎进程的退出码原样返回给调用方。Godot 脚本错误通常打印到 stdout/stderr 但不会令进程自行退出，因此脚本在轮询到错误输出时会杀进程。
