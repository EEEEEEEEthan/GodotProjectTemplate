extends Node
## Game MCP 单例：启动 HTTP 服务并分发已注册协议回调。

const PLUGIN_CONFIG_PATH := "res://addons/game_mcp/plugin.cfg"

var _handlers: Dictionary = {}
var _server: Node


func _ready() -> void:
	if not _is_plugin_enabled():
		return
	_server = ApplicationMcpServer.new()
	add_child(_server)
	_server.command_received.connect(_on_command_received)
	var port: int = _server.start()
	if port > 0:
		print("Game MCP: HTTP 服务已启动，端口 %d" % port)


func _is_plugin_enabled() -> bool:
	var enabled_plugins: PackedStringArray = ProjectSettings.get_setting("editor_plugins/enabled")
	return enabled_plugins.has(PLUGIN_CONFIG_PATH)


func register_handle(handle: Object) -> void:
	var command_name := _resolve_command_name(handle)
	if command_name.is_empty():
		push_error("Game MCP: handle 缺少 command")
		return
	if not handle.has_method("on_receive"):
		push_error("Game MCP: handle 缺少 on_receive 方法")
		return
	_handlers[command_name] = handle


func unregister_handle(command_name: String) -> void:
	_handlers.erase(command_name)


func get_listening_port() -> int:
	if _server == null:
		return -1
	return _server.get_listening_port()


func _resolve_command_name(handle: Object) -> String:
	if handle.has_method("get_command"):
		return str(handle.get_command())
	return str(handle.get("command"))


func _on_command_received(command: String, data: Dictionary, respond: Callable) -> void:
	if not _handlers.has(command):
		respond.call({"ok": false, "error": "未注册的命令: %s" % command})
		return
	var handle: Object = _handlers[command]
	handle.on_receive(
		command,
		data,
		func(result: Dictionary) -> void:
			if typeof(result) != TYPE_DICTIONARY:
				respond.call({"ok": false, "error": "回调必须返回 Dictionary"})
				return
			respond.call({"ok": true, "data": result})
	)
