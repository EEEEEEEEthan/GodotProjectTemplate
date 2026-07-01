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

需要 Python 3.10+。`ide_mcp.bat` 会自动安装依赖。

完成以上两步即可，无需在场景里注册 handler。

## 脚本格式

POST body 即 GDScript 全文，须 `extends RefCounted` 并定义：

```gdscript
extends RefCounted

func run(scene_tree: SceneTree) -> Variant:
    var player = scene_tree.current_scene.get_node("Player")
    return {"hp": player.hp, "pos": str(player.global_position)}
```

## 获取端口号

游戏启动后日志会打印：

```
<<<GAME_MCP::PORT=6789>>>
```

`run` 必须用这个端口，不要硬编码 `6789`（占用时会自动递增）。

Agent 流程：

1. 启动游戏，等待 `<<<GAME_MCP::PORT=XXXX>>>`
2. `run(port=XXXX, script="...")`
3. 结束后关闭游戏
