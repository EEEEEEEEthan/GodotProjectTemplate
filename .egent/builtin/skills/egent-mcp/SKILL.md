---
name: egent-mcp
description: Game MCP 连通性说明与验证。关注 egent 侧桥接与游戏 HTTP 服务是否接通；具体 command 由玩法层 handler 决定，不在本技能范围。
---

# Game MCP 连通性

## 架构（两段）

```text
Agent (mcp_bridge)  ←stdio→  godot_mcp.server  ←HTTP→  GodotMcp (游戏进程)
                              game_command 工具         POST /mcp
```

| 层级 | 位置 | 职责 |
|------|------|------|
| Agent 桥接 | `.egent/builtin/agent/mcp_bridge.py` | 启动 stdio MCP 服务、发现 `game_command` 工具 |
| MCP 转发 | `addons/godot_mcp/server.py` | 将 `game_command` 转为 HTTP 请求 |
| 游戏 HTTP | `addons/godot_mcp/godot_mcp.gd` | 监听端口、解析 POST `/mcp`、回调 handler |
| 命令分发 | 玩法层（如 `mcp_handler.gd`） | `on_receive` 中 `match command`，决定支持哪些指令 |

**边界**：`GodotMcp` 只负责 HTTP 传输与 JSON 封装；能接收什么 `command` 由实例化时传入的 handler 决定，属于玩法层，egent 基础设施不维护具体指令表。

## 握手标记

游戏启动后，`GodotMcp.start()` 成功会打印：

```text
<<<EGENT::GAME_MCP::HANDSHAKE::v1::port=8765>>>
```

绑定失败则打印 `<<<EGENT::GAME_MCP::HANDSHAKE::v1::BIND_FAILED>>>`。

`launch_game` 工具轮询启动日志获取端口；也可手动在 `.egent/.temp/game_*.log` 中查找。

## 验证清单

### 1. Agent 桥接（无需游戏）

```text
python .egent/builtin/skills/egent-test/run.py
```

`test_mcp_bridge.py` 覆盖：桥接生命周期、共享单例、关闭期 cancel scope 容错。

### 2. 游戏 HTTP 服务（无需 command）

`launch_game` 返回 `MCP 端口：XXXX` 即表示 `GodotMcp` 已监听。失败时检查日志中的 `BIND_FAILED` 或握手超时。

### 3. 端到端（可选）

需游戏已启动且玩法层 handler 已实现探测命令（本项目 `mcp_handler.gd` 提供 `ping`）：

```text
game_command(port=PORT, command="ping", data={})
```

预期：`{"ok": true, "data": {"pong": true}}`。

此步验证 HTTP → handler → response 全链路；若失败，先区分是传输问题还是玩法层未注册该 command。

## 配置

默认 MCP 服务定义在 `agent/data_loader.py` 的 `DEFAULT_MCP`，可通过 `.agents/mcp.json` 或 `%LOCALAPPDATA%/Egent/mcp.json` 覆盖。

## 相关技能

- `.agents/skills/godot-mcp-eval` — 玩法层 `eval` 命令的使用（运行时 GDScript 探查）
- `.egent/builtin/skills/egent-test` — 运行全部 egent 单元测试
