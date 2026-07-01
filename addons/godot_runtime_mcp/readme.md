# Godot Runtime MCP

## 使用场景

- Agent 对**运行中的游戏**做 debug（查节点、读变量、触发 UI）
- Agent 做白盒测试（断言运行时状态、驱动游戏流程）
- Agent 动态执行 GDScript 探查场景，无需改项目文件

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

需要 Python 3.10+。`ide_mcp.bat` 会自动安装依赖。

### 3. 注册 handler

入口场景 `_ready`：

```gdscript
func _ready() -> void:
    GameMcp.handler = on_command_received


func on_command_received(data: Dictionary) -> Variant:
    var command: String = data.get("command", "")
    match command:
        "ping":
            return "pong"
        _:
            return "error: unknown command: %s" % command
```

完整示例：`res://main.tscn`

## Handler 示例

### ping

```gdscript
if command == "ping":
    return "pong"
```

### execute（Agent 动态脚本）

```gdscript
elif command == "execute":
    var script_source: String = data.get("script", "")
    var gdscript := GDScript.new()
    gdscript.source_code = script_source
    gdscript.resource_path = "mcp-dynamic://%d" % randi()
    if gdscript.reload() != OK:
        return "error: compilation failed"
    var instance = gdscript.new()
    if not instance.has_method("run"):
        return "error: script missing run(scene_tree) method"
    return await instance.run(get_tree())
```

`data.script` 示例：

```gdscript
func run(scene_tree: SceneTree) -> Variant:
    var player = scene_tree.current_scene.get_node("Player")
    return {"hp": player.hp, "pos": str(player.global_position)}
```

### get_node_info

```gdscript
elif command == "get_node_info":
    var path: String = data.get("path", "")
    var node := get_node_or_null(path)
    if node == null:
        return {"error": "node not found", "path": path}
    return {"path": path, "type": node.get_class()}
```

### trigger

```gdscript
elif command == "trigger":
    match data.get("action", ""):
        "start_battle":
            $GameState.start_battle()
            return {"ok": true}
        "add_gold":
            $Wallet.add(data.get("amount", 0))
            return {"gold": $Wallet.gold}
    return {"error": "unknown action"}
```

## 获取端口号

游戏启动后日志会打印：

```
<<<GAME_MCP::PORT=6789>>>
```

`send` 必须用这个端口，不要硬编码 `6789`（占用时会自动递增）。

**方式一**：从日志搜索 `<<<GAME_MCP::PORT=(\d+)>>>`

**方式二（推荐）**：让 Agent 启动游戏并捕获日志，见到端口标记后再调 `send`：

```powershell
.\.engine\.engine.exe --path . res://main.tscn
```

Agent 流程：

1. 启动游戏，等待 `<<<GAME_MCP::PORT=XXXX>>>`
2. `send(port=XXXX, data=...)`
3. 结束后关闭游戏
