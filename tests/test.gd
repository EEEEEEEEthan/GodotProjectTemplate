class_name Test
extends SceneTree

static func has_autotest_argument() -> bool:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	return user_arguments.has("--autotest")

static func read_autotest_name_from_command_line() -> String:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	for argument_index in user_arguments.size():
		if user_arguments[argument_index] == "--autotest" and argument_index + 1 < user_arguments.size():
			return user_arguments[argument_index + 1]
	return ""

func _init() -> void:
	if not has_autotest_argument():
		return
	var test_name: String = Test.read_autotest_name_from_command_line()
	if test_name.is_empty():
		push_error("Missing test name after --autotest")
		quit(1)
		return
	run_named(test_name)

func run_named(test_name: String) -> void:
	const TESTS_DIR := "res://tests/"
	var dir := DirAccess.open(TESTS_DIR)
	if dir == null:
		push_error("Failed to open tests directory: " + TESTS_DIR)
		quit(1)
		return

	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.ends_with("_test.gd"):
			# Derive test name: "hello_test.gd" -> "hello"
			var derived_name := file_name.trim_suffix(".gd").trim_suffix("_test")
			if derived_name == test_name:
				var script_path := TESTS_DIR + file_name
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
				return
		file_name = dir.get_next()
	dir.list_dir_end()

	push_error("'%s' not found" % test_name)
	quit(1)

static func _has_static_method(script: Script, method_name: String) -> bool:
	for method in script.get_script_method_list():
		if method["name"] == method_name and method["flags"] & METHOD_FLAG_STATIC:
			return true
	return false
