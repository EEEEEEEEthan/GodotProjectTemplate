# 启动

`.engine-edit.bat`自动下载引擎并且打开编辑器

# 自动化测试

`egent.bat --test <脚本路径>` 单项测试
`egent.bat --test-folder <目录>` 全量测试（自动发现目录下全部 .gd）

# Game MCP

游戏运行时通过 HTTP 接收 IDE 指令。

## IDE 侧 MCP 配置

安装依赖：

```bash
pip install .python
```

在 Cursor 的 MCP 设置（`~/.cursor/mcp.json` 或项目 `.cursor/mcp.json`）中添加：

```json
{
  "mcpServers": {
	"godot-game": {
	  "command": "python",
	  "args": ["-m", "egent.mcp.server"],
	  "cwd": "C:/Projects/Template"
	}
  }
}
```
