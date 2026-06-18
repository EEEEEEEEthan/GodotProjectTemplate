# 新增测试

## 清单

- [ ] 选定 `TESTNAME`（英文标识符，描述测试意图）
- [ ] 在 `tests/` 新增测试类，实现 `run() -> int`
- [ ] 在 `tests/test.gd` 的 `_TEST_TYPES` 注册 `TESTNAME`
- [ ] 在 `.engine-test-full.bat` 的 `for %%t in (...)` 中加入同一 `TESTNAME`
- [ ] 本地运行 `.engine-test.bat TESTNAME` 验证
- [ ] 运行 `.engine-test-full.bat` 验证全量

## `.engine-test-full.bat` 注册示例

```bat
REM Registered test names; keep in sync with tests/test.gd
for %%t in (hellotest another_case) do (
```

## 测试类示例

```gdscript
class_name HelloTest
extends RefCounted

func run() -> int:
	print("hellotest")
	return 0
```

## 测试逻辑建议

- 单测聚焦一件事；名字能直接看出测什么
- 失败路径要有可读日志（`push_error` / `printerr`）
- 异步测试在 `run()` 内 `await` 完成后再返回退出码
- 不依赖编辑器 UI；headless 可跑

## 不要做的事

- 不要新建 `.autotest-registry` 或其它旁路注册文件
- 不要在 `.bat` 里写中文
- 不要只在 `tests/test.gd` 注册而忘记更新 `.engine-test-full.bat`
