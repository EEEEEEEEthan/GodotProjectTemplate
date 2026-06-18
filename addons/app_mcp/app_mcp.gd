extends Node
class_name ApplicationMcp
## Game MCP 单例：启动 HTTP 服务并分发已注册协议回调。

const PLUGIN_CONFIG_PATH := "res://addons/app_mcp/plugin.cfg"
const DEFAULT_PORT := 8765
const MAX_PORT_ATTEMPTS := 100
const ROUTE_PATH := "/mcp"

var _handler = func(command: String, data: Dictionary, respond: Callable) -> void: pass
var _tcp_server := TCPServer.new()
var _connections: Array[Dictionary] = []
var _listening_port: int = -1


func _init(handler: Callable) -> void:
	_handler = handler
	var port: int = start()
	if port > 0:
		print("Game MCP: HTTP 服务已启动，端口 %d" % port)

func register_handle(handle: Object) -> void:
	var command_name := _resolve_command_name(handle)
	if command_name.is_empty():
		push_error("Game MCP: handle 缺少 command")
		return
	if not handle.has_method("on_receive"):
		push_error("Game MCP: handle 缺少 on_receive 方法")
		return
	_handler = handle


func get_listening_port() -> int:
	return _listening_port


func start(preferred_port: int = 0) -> int:
	var port := preferred_port if preferred_port > 0 else DEFAULT_PORT
	for _attempt in MAX_PORT_ATTEMPTS:
		if _tcp_server.listen(port) == OK:
			_listening_port = port
			set_process(true)
			return port
		port += 1
	push_error("Game MCP: 无法绑定端口")
	return -1


func _resolve_command_name(handle: Object) -> String:
	if handle.has_method("get_command"):
		return str(handle.get_command())
	return str(handle.get("command"))


func _on_command_received(command: String, data: Dictionary, respond: Callable) -> void:
	_handler.call(
		command,
		data,
		func(result: Dictionary) -> void:
			if typeof(result) != TYPE_DICTIONARY:
				respond.call({"ok": false, "error": "回调必须返回 Dictionary"})
				return
			var response_body := {"ok": true, "data": result}
			respond.call(response_body)
	)


func _process(_delta: float) -> void:
	while _tcp_server.is_connection_available():
		var peer := _tcp_server.take_connection()
		_connections.append({
			"peer": peer,
			"buffer": PackedByteArray(),
			"state": "reading",
			"body_length": 0,
			"responded": false,
		})
	for connection_index in range(_connections.size() - 1, -1, -1):
		_poll_connection(_connections[connection_index], connection_index)


func _poll_connection(connection: Dictionary, connection_index: int) -> void:
	var peer: StreamPeerTCP = connection.peer
	if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		_close_connection(connection_index)
		return
	var available_bytes := peer.get_available_bytes()
	if available_bytes > 0:
		var read_result := peer.get_data(available_bytes)
		if read_result[0] != OK:
			_close_connection(connection_index)
			return
		connection.buffer.append_array(read_result[1])
	if connection.state == "reading" and _try_finish_reading(connection):
		_dispatch_request(connection)
	if connection.responded:
		_close_connection(connection_index)


func _try_finish_reading(connection: Dictionary) -> bool:
	var buffer: PackedByteArray = connection.buffer
	var delimiter := "\r\n\r\n"
	var buffer_text := buffer.get_string_from_utf8()
	var header_end := buffer_text.find(delimiter)
	if header_end < 0:
		return false
	var header_text := buffer_text.substr(0, header_end)
	var body_start := header_end + delimiter.length()
	var body_length := _read_content_length(header_text)
	if buffer.size() < body_start + body_length:
		return false
	connection.state = "ready"
	connection.body_length = body_length
	connection.header_text = header_text
	connection.body_bytes = buffer.slice(body_start, body_start + body_length)
	return true


func _read_content_length(header_text: String) -> int:
	for header_line in header_text.split("\r\n"):
		var lower_line := header_line.to_lower()
		if lower_line.begins_with("content-length:"):
			return header_line.split(":", true, 1)[1].strip_edges().to_int()
	return 0


func _dispatch_request(connection: Dictionary) -> void:
	var header_text: String = connection.header_text
	var request_line := header_text.split("\r\n", false)[0]
	var request_parts := request_line.split(" ")
	if request_parts.size() < 2:
		_send_json_response(connection, 400, {"ok": false, "error": "无效请求行"})
		return
	var method := request_parts[0]
	var path := request_parts[1]
	if method != "POST" or path != ROUTE_PATH:
		_send_json_response(connection, 404, {"ok": false, "error": "仅支持 POST %s" % ROUTE_PATH})
		return
	var body_text: String = connection.body_bytes.get_string_from_utf8()
	var json := JSON.new()
	if json.parse(body_text) != OK:
		_send_json_response(connection, 400, {"ok": false, "error": "JSON 解析失败"})
		return
	var payload: Variant = json.data
	if typeof(payload) != TYPE_DICTIONARY:
		_send_json_response(connection, 400, {"ok": false, "error": "请求体必须是 JSON 对象"})
		return
	var command: String = str(payload.get("command", ""))
	if command.is_empty():
		_send_json_response(connection, 400, {"ok": false, "error": "缺少 command 字段"})
		return
	var data: Dictionary = payload.get("data", {})
	if typeof(data) != TYPE_DICTIONARY:
		data = {}
	print("Game MCP: 收到 command=%s data=%s" % [command, JSON.stringify(data)])
	connection.state = "dispatched"
	_on_command_received(
		command,
		data,
		func(response_body: Dictionary) -> void:
			_send_json_response(connection, 200, response_body)
	)


func _send_json_response(connection: Dictionary, status_code: int, response_body: Dictionary) -> void:
	if connection.responded:
		return
	var peer: StreamPeerTCP = connection.peer
	var body_text := JSON.stringify(response_body)
	print("Game MCP: 发送 %s" % body_text)
	var status_text := "OK"
	if status_code == 400:
		status_text = "Bad Request"
	elif status_code == 404:
		status_text = "Not Found"
	var response_text := "HTTP/1.1 %d %s\r\nContent-Type: application/json\r\nContent-Length: %d\r\nConnection: close\r\n\r\n%s" % [
		status_code,
		status_text,
		body_text.to_utf8_buffer().size(),
		body_text,
	]
	peer.put_data(response_text.to_utf8_buffer())
	connection.responded = true


func _close_connection(connection_index: int) -> void:
	var connection: Dictionary = _connections[connection_index]
	var peer: StreamPeerTCP = connection.peer
	peer.disconnect_from_host()
	_connections.remove_at(connection_index)
