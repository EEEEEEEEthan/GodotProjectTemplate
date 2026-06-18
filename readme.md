# 启动

`.engine-edit.bat`自动下载引擎并且打开编辑器

# Game MCP

游戏运行时通过 HTTP 接收 IDE 指令。启用 **Project → Plugins → Game MCP** 后，启动游戏会在命令行打印端口。

## 协议

`POST /mcp`，JSON 请求体：

```json
{
  "command": "ping",
  "data": {}
}
```

响应：

```json
{
  "ok": true,
  "data": {}
}
```

## 游戏侧注册回调

```gdscript
func _ready() -> void:
    GameMcp.register_handle(MyHandler.new())

class MyHandler:
    var command := "my_command"

    func on_receive(data: Dictionary, return_callback: Callable) -> void:
        return_callback.call({"result": data})
```

也可继承 `GameMcpHandler` 基类。

## IDE 侧 MCP 配置

安装依赖：

```bash
pip install -r .mcp/requirements.txt
```

在 Cursor 的 MCP 设置（`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）中添加：

```json
{
  "mcpServers": {
    "godot-game": {
      "command": "python",
      "args": ["C:/Projects/Template/.mcp/server.py"]
    }
  }
}
```

将路径替换为本机项目绝对路径。Windows 若 `python` 不在 PATH，可改为 `py` 或完整解释器路径。

## MCP 工具

| 工具 | 说明 |
|------|------|
| `game_command` | 向指定端口游戏发送命令（`port`, `command`, `data`, `timeout_seconds`） |

示例：游戏启动后命令行显示 `Game MCP: HTTP 服务已启动，端口 8765`，则调用 `game_command(port=8765, command="ping")`。

## 多实例

每个游戏进程独立端口；`game_command` 的 `port` 参数指定目标实例。
