---
name: godot-autotest
description: 本项目 Godot 引擎自动化测试流程（.engine-test.ps1、autotest 节点注册与分发）。新增/运行/编写自动化测试、实现 --autotest 测试节点、或维护 .engine-test-full.bat 注册表时使用。
---

# 自动化测试

先读本文件索引；落到具体步骤时再读对应条目。

## 运行

```powershell
.\.engine-test.ps1 TESTNAME
.\.engine-test.ps1 TESTNAME -Headless
.\.engine-test-full.bat
.\.engine-test-full.bat --headless
```

**import 固定 `--headless`**；**跑测试默认不加 `-Headless`**，走正常 GPU 渲染。仅 CI、无窗口环境或明确不依赖画面时，单测传 `-Headless`，全量传 `--headless`（转发给各单测）。

单测走 `.engine-test.ps1`：无 `-IgnorePrepare` 时先 prepare，再 `--headless --import`；`-Headless` 只影响 autotest 阶段。脚本轮询输出，命中 `SCRIPT ERROR` / `Parse Error` / `ERROR: Failed` 或超时则杀进程。

全量走 `.engine-test-full.bat`：prepare 与 import（headless）各一次，再逐个调用 `.engine-test.ps1 -IgnorePrepare`；可选 `--headless` 透传给各单测。

## 架构

`--autotest TESTNAME` 启动 `.engine/.engine.exe` 后，主场景读取 `TESTNAME` 并交给 `tests/test.gd`（`RefCounted`）分发到对应测试类；测试类实现 `run() -> int`，结束时 `get_tree().quit(exit_code)`（`0` 通过，非 `0` 失败）。

详见 [autotest-node.md](entries/autotest-node.md)。

## 新增测试

1. 在 `tests/` 新增测试类（`extends RefCounted`，实现 `run() -> int`）
2. 在 `tests/test.gd` 的 `_TEST_TYPES` 注册 `TESTNAME`
3. 将同名 `TESTNAME` 加入 `.engine-test-full.bat` 的 `for %%t in (...)` 列表

两处注册必须保持一致。详见 [add-test.md](entries/add-test.md)。

## 约束

- 测试相关脚本放在 `tests/` 目录
- **import 固定 headless**；**跑测试默认不加 `-Headless`**；依赖渲染的测试必须不开 headless
- `.bat` 文件内容只用英文（echo、REM、变量名等）
- 测试名使用英文标识符，与 autotest 节点注册键一致
- 不要引入外部注册表文件；全量列表只写在 `.engine-test-full.bat`

## 相关技能

实现 autotest 节点 GDScript 时读 `godot-script`、`godot-engine`。
