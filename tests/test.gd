class_name Test
extends SceneTree

func _init() -> void:
	if not has_autotest_argument():
		return
	var test_name: String = Test.read_autotest_name_from_command_line()
	if test_name.is_empty():
		push_error("Missing test name after --autotest")
		quit(1)
		return
	run_named(test_name)


static func has_autotest_argument() -> bool:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	return user_arguments.has("--autotest")


static func read_autotest_name_from_command_line() -> String:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	for argument_index in user_arguments.size():
		if user_arguments[argument_index] == "--autotest" and argument_index + 1 < user_arguments.size():
			return user_arguments[argument_index + 1]
	return ""


func _run() -> void:
	print("run")

func run_named(test_name: String) -> void:
	match test_name:
		"hellotest":
			HelloTest.run(self)
			return
	push_error("'%s' not found" % test_name)
	quit(1)
