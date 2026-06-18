# Test 分发器

## 职责

`tests/test.gd`（`class_name Test`，`RefCounted`）负责：

1. 从命令行读取 `--autotest` 后的 `TESTNAME`
2. 在注册表查找对应测试类
3. 实例化并调用 `run() -> int`

主场景 `main/main.gd` 在 `_ready` 中检测 `--autotest`；有则分发并 `quit`，无则正常启动。

## 命令行解析

使用 `OS.get_cmdline_args()` 扫描 `--autotest`，下一项即为 `TESTNAME`。

未传 `--autotest` 时，主场景不应干扰正常启动。

## 注册与分发

在 `Test._TEST_TYPES` 维护 `TESTNAME -> TestClass`。每个测试类放在 `tests/`，`extends RefCounted`，实现 `run() -> int`。

```gdscript
const _TEST_TYPES: Dictionary = {
	"hellotest": HelloTest,
}

func run_named(test_name: String) -> int:
	if not _TEST_TYPES.has(test_name):
		push_error("Unknown autotest: %s" % test_name)
		return 1
	var test_type: Variant = _TEST_TYPES[test_name]
	return int(test_type.new().run())
```

## 退出码

| 结果 | `run()` / `quit` |
|------|------------------|
| 通过 | `0` |
| 断言/逻辑失败 | `1`（或约定非零码） |
| 未知测试名 | `1` |

`.engine-test.ps1` 将引擎进程的退出码原样返回给调用方。Godot 脚本错误通常打印到 stdout/stderr 但不会令进程自行退出，因此脚本在轮询到错误输出时会杀进程。
