extends Node

var handler: Callable
var port: int = 6789
var _tcp_server := TCPServer.new()
var _connections: Array[Dictionary] = []

func _ready() -> void:
	while not _start(port):
		port += 1
	print("<<<EGENT::GAME_MCP::HANDSHAKE::v1::port=%d>>>" % port)

func _start(port: int) -> bool:
	if _tcp_server.listen(port) == OK:
		self.port = port
		set_process(true)
		return true
	return false

func _on_command_received(data: Dictionary):
	var result = await handler.call(data)
	return result


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
		_send_error_response(connection, 400, "无效请求行")
		return
	var method := request_parts[0]
	var body_text: String = connection.body_bytes.get_string_from_utf8()
	var json := JSON.new()
	if json.parse(body_text) != OK:
		_send_error_response(connection, 400, "JSON 解析失败")
		return
	var data: Variant = json.data
	if typeof(data) != TYPE_DICTIONARY:
		_send_error_response(connection, 400, "请求体必须是 JSON 对象")
		return
	print("Game MCP: 收到 data=%s" % body_text)
	connection.state = "dispatched"
	var result = await _on_command_received(data)
	_send_ok_response(connection, result)


func _send_ok_response(connection: Dictionary, data: Variant) -> void:
	_send_json_response(connection, 200, {"ok": true, "data": data})


func _send_error_response(connection: Dictionary, status_code: int, error: String) -> void:
	_send_json_response(connection, status_code, {"ok": false, "error": error})


func _send_json_response(connection: Dictionary, status_code: int, body: Variant) -> void:
	if connection.responded:
		return
	var peer: StreamPeerTCP = connection.peer
	var body_text := JSON.stringify(body)
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
