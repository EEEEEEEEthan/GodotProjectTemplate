---
name: godot-autotest
description: 本项目 Godot 引擎自动化测试流程（.engine-test.ps1、autotest 节点注册与分发）。新增/运行/编写自动化测试、实现 --autotest 测试节点、或维护 .engine-test-full.bat 注册表时使用。
---

# 自动化测试

## 运行

```powershell
.\.engine-test.ps1 TESTNAME
.\.engine-test.ps1 TESTNAME -Headless
.\.engine-test-full.bat
.\.engine-test-full.bat --headless
```

跑测试默认不加 headless，走正常 GPU 渲染。CI、无窗口环境或明确不依赖画面时，单测加 `-Headless`，全量加 `--headless`。

## 新增测试

1. 在 `tests/` 新增测试类
2. 在 `tests/test.gd` 的 `run_named` match 中注册 `TESTNAME`
3. 将同名 `TESTNAME` 加入 `.engine-test-full.bat` 的 `for %%t in (...)` 列表

两处注册必须保持一致。详见 [add-test.md](entries/add-test.md)。

## 约束

- 用 `.\.engine-test.ps1` 跑单测，不要手动启动引擎或传 `--script`
- 测试相关脚本放在 `tests/` 目录
- 跑测试默认不加 headless；依赖渲染的测试必须不开 headless
- `.bat` 文件内容只用英文（echo、REM、变量名等）
- 测试名使用英文标识符
- 不要引入外部注册表文件；全量列表只写在 `.engine-test-full.bat`
