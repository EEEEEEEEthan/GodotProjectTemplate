# Autotest 节点

## 职责

1. 检测 `--autotest` 是否在命令行参数中
2. 读取紧随其后的 `TESTNAME`
3. 在注册表查找并执行对应测试
4. 根据结果退出引擎

## 命令行解析

使用 `OS.get_cmdline_user_args()`（或项目约定的等价方式）扫描 `--autotest`，下一项即为 `TESTNAME`。

未传 `--autotest` 时，autotest 入口不应干扰正常启动。

## 注册与分发

维护 `TESTNAME -> Callable`（或等价映射）。未知名字应打印明确错误并以非零退出码结束。

```gdscript
var _tests: Dictionary = {
    "example_smoke": _run_example_smoke,
}

func _dispatch(test_name: String) -> void:
    var runner: Callable = _tests.get(test_name)
    if runner.is_null():
        push_error("Unknown autotest: %s" % test_name)
        get_tree().quit(1)
        return
    var exit_code: int = int(runner.call())
    get_tree().quit(exit_code)
```

## 挂载方式

任选一种与项目一致的入口（Autoload、主场景子节点、或 `project.godot` 专用运行场景），保证带 `--autotest` 时一定会跑到分发逻辑。

## 退出码

| 结果 | `quit` 参数 |
|------|-------------|
| 通过 | `0` |
| 断言/逻辑失败 | `1`（或约定非零码） |
| 未知测试名 | `1` |

`.engine-test.bat` 将引擎进程的退出码原样返回给调用方。
