extends Node

func _ready():
	add_child(ApplicationMcp.new(on_receive))

func on_receive(command: String, data: Dictionary, response: Callable) -> void:
	match command:
		&"ping":
			response.call({&"pong": true})
		&"eval":
			response.call(_eval_gdscript(data))

func _eval_gdscript(data: Dictionary) -> Dictionary:
	var source := str(data.get(&"source", ""))
	var file_path := str(data.get(&"file", ""))
	if not file_path.is_empty():
		if not FileAccess.file_exists(file_path):
			return {&"error": &"文件不存在: %s" % file_path}
		source = FileAccess.get_file_as_string(file_path)
	if source.is_empty():
		return {&"error": &"缺少 source 或 file"}
	var script := GDScript.new()
	script.source_code = source
	var reload_error := script.reload()
	if reload_error != OK:
		return {&"error": &"编译失败: %s" % error_string(reload_error)}
	var script_instance: Variant = script.new()
	if not script_instance.has_method(&"run"):
		return {&"error": &"脚本缺少 run(scene_tree) 方法"}
	return {&"result": _json_safe(script_instance.run(get_tree()))}

func _json_safe(value: Variant) -> Variant:
	match typeof(value):
		TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING:
			return value
		TYPE_ARRAY:
			var items: Array = []
			for item in value:
				items.append(_json_safe(item))
			return items
		TYPE_DICTIONARY:
			var output: Dictionary = {}
			for entry_key in value:
				output[str(entry_key)] = _json_safe(value[entry_key])
			return output
		_:
			return str(value)
