# Godot Runtime MCP

运行时向 Godot 发送 GDScript 并执行，用于 debug、白盒测试、探查场景状态。

## 接入

### 1. Autoload

**项目 → 项目设置 → Autoload**，添加：

```
res://addons/godot_runtime_mcp/game_mcp.gd
```

节点名：`GameMcp`

### 2. MCP 配置

项目根 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "godot-game": {
      "command": "addons/godot_runtime_mcp/ide_mcp.bat"
    }
  }
}
```

需要 Python 3.10+。

### 3. 获取端口号

游戏启动后日志会打印：

```
<<<GAME_MCP::PORT=6789>>>
```

`run` 默认用这个端口，不要硬编码 `6789`（占用时会自动递增）。

也可以让agent自行启动游戏，他会自动将日志纳入上下文

### 4. 命令agent

提示词示例

```
用mcp查看一下当前游戏6789端口的场景树
```