# Godot Runtime MCP

Send GDScript to a running Godot instance and execute it at runtime—for debugging, white-box testing, and inspecting scene state.

## Setup

### 1. Autoload

In **Project → Project Settings → Autoload**, add:

```
res://addons/godot_runtime_mcp/game_mcp.gd
```

Node name: `GameMcp`

### 2. MCP configuration

In the project root `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "godot-game": {
      "command": "addons/godot_runtime_mcp/ide_mcp.bat"
    }
  }
}
```

Requires Python 3.10+.

### 3. Get the port number

After the game starts, the log prints:

```
<<<GAME_MCP::PORT=6789>>>
```

You can also have the agent launch the game itself—it will automatically include the log in context.

### 4. Prompt the agent

Example prompt:

```
Use MCP to inspect the scene tree on game port 6789
```
