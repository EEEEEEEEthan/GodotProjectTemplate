---
name: godot-autotest
description: 本项目 Godot 引擎自动化测试流程（.engine-test.bat、autotest 节点注册与分发）。新增/运行/编写自动化测试、实现 --autotest 测试节点、或维护 .engine-test-full.bat 注册表时使用。
---

# 自动化测试

先读本文件索引；落到具体步骤时再读对应条目。

## 运行

```bat
.engine-test.bat TESTNAME
.engine-test-full.bat
```

单测走 `.engine-test.bat TESTNAME`：先 `call .engine-prepare.bat`，再 `--headless --import` 强制导入资源，最后 `--autotest`。

全量走 `.engine-test-full.bat`：只执行一次 prepare 与 import，再逐个运行已注册测试。

## 架构

`--autotest TESTNAME` 启动 `.engine/.engine.exe` 后，项目加载额外 autotest 入口节点；节点从命令行解析 `TESTNAME`，按名字分发到已注册测试逻辑，结束时 `get_tree().quit(exit_code)`（`0` 通过，非 `0` 失败）。

详见 [autotest-node.md](entries/autotest-node.md)。

## 新增测试

1. 在 autotest 节点注册 `TESTNAME` 并实现对应逻辑
2. 将同名 `TESTNAME` 加入 `.engine-test-full.bat` 的 `for %%t in (...)` 列表

两处注册必须保持一致。详见 [add-test.md](entries/add-test.md)。

## 约束

- `.bat` 文件内容只用英文（echo、REM、变量名等）
- 测试名使用英文标识符，与 autotest 节点注册键一致
- 不要引入外部注册表文件；全量列表只写在 `.engine-test-full.bat`

## 相关技能

实现 autotest 节点 GDScript 时读 `godot-script`、`godot-engine`。
