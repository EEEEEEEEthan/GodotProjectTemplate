extends Node

class _RunOutputCapture extends Logger:
	var _mutex := Mutex.new()
	var _lines: PackedStringArray = []

	func _log_message(message: String, error: bool) -> void:
		if error:
			return
		_mutex.lock()
		_lines.append(message)
		_mutex.unlock()

	func collect() -> String:
		_mutex.lock()
		var text := "\n".join(_lines)
		_mutex.unlock()
		return text

var _port: int = 6789
var _tcp_server := TCPServer.new()
var _connections: Array[Dictionary] = []
var _dynamic_script_count := 0

func _ready() -> void:
	while not _start(_port):
		_port += 1
	print("<<<GAME_MCP::PORT=%d>>>" % _port)

func _start(port: int) -> bool:
	if _tcp_server.listen(_port) == OK:
		set_process(true)
		return true
	return false

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
	var script_source: String = connection.body_bytes.get_string_from_utf8()
	if script_source.is_empty():
		_send_error_response(connection, 400, "script is empty")
		return
	print("Game MCP: received script (%d bytes)" % script_source.length())
	connection.state = "dispatched"
	var result = await _execute_script(script_source)
	_send_ok_response(connection, result)

func _execute_script(script_source: String) -> Variant:
	await get_tree().process_frame
	_dynamic_script_count += 1
	var gdscript := GDScript.new()
	gdscript.source_code = script_source
	gdscript.resource_path = "mcp-dynamic://%d" % _dynamic_script_count
	if gdscript.reload() != OK:
		return "error: compilation failed"
	var script_instance = gdscript.new()
	if not script_instance is RefCounted:
		return "error: script must extend RefCounted"
	if not script_instance.has_method("run"):
		return "error: script missing run(scene_tree) method"
	var output_capture := _RunOutputCapture.new()
	OS.add_logger(output_capture)
	var run_result = await script_instance.run(get_tree())
	OS.remove_logger(output_capture)
	return {
		"value": run_result,
		"stdout": output_capture.collect(),
	}

func _send_ok_response(connection: Dictionary, data: Variant) -> void:
	_send_json_response(connection, 200, {"ok": true, "data": data})

func _send_error_response(connection: Dictionary, status_code: int, error: String) -> void:
	_send_json_response(connection, status_code, {"ok": false, "error": error})

func _send_json_response(connection: Dictionary, status_code: int, body: Variant) -> void:
	if connection.responded:
		return
	var peer: StreamPeerTCP = connection.peer
	var body_text := JSON.stringify(body)
	print("Game MCP: sent %s" % body_text)
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
