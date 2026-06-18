# 新增测试

## 清单

- [ ] 选定 `TESTNAME`（英文标识符，描述测试意图）
- [ ] 在 autotest 节点注册表添加 `TESTNAME` 并实现 runner
- [ ] 在 `.engine-test-full.bat` 的 `for %%t in (...)` 中加入同一 `TESTNAME`
- [ ] 本地运行 `.engine-test.bat TESTNAME` 验证
- [ ] 运行 `.engine-test-full.bat` 验证全量

## `.engine-test-full.bat` 注册示例

```bat
REM Registered test names; keep in sync with the autotest node
for %%t in (example_smoke another_case) do (
```

## 测试逻辑建议

- 单测聚焦一件事；名字能直接看出测什么
- 失败路径要有可读日志（`push_error` / `printerr`）
- 异步测试在 runner 内 `await` 完成后再返回退出码；不要让节点在测试未完成时提前 `quit`
- 不依赖编辑器 UI；headless 可跑

## 不要做的事

- 不要新建 `.autotest-registry` 或其它旁路注册文件
- 不要在 `.bat` 里写中文
- 不要只在 Godot 侧注册而忘记更新 `.engine-test-full.bat`
