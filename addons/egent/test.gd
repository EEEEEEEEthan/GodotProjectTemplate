class_name Test
extends SceneTree

static func has_autotest_argument() -> bool:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	return user_arguments.has("--autotest")

static func read_autotest_script_from_command_line() -> String:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	for argument_index in user_arguments.size():
		if user_arguments[argument_index] == "--autotest" and argument_index + 1 < user_arguments.size():
			return user_arguments[argument_index + 1]
	return ""

func _init() -> void:
	if not has_autotest_argument():
		return
	var script_path: String = Test.read_autotest_script_from_command_line()
	if script_path.is_empty():
		push_error("Missing test script path after --autotest")
		quit(1)
		return
	run_script(script_path)

func run_script(script_path: String) -> void:
	if not script_path.begins_with("res://"):
		push_error("Invalid test script path: " + script_path)
		quit(1)
		return

	var script := load(script_path)
	if script == null:
		push_error("Failed to load test script: " + script_path)
		quit(1)
		return
	if not _has_static_method(script, "run"):
		push_error("Test script missing static run(): " + script_path)
		quit(1)
		return
	script.run(self)

static func _has_static_method(script: Script, method_name: String) -> bool:
	for method in script.get_script_method_list():
		if method["name"] == method_name and method["flags"] & METHOD_FLAG_STATIC:
			return true
	return false
