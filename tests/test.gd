class_name Test
extends RefCounted

const HelloTest = preload("res://tests/hello_test.gd")

const _TEST_TYPES: Dictionary = {
	"hellotest": HelloTest,
}


static func has_autotest_argument() -> bool:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	return user_arguments.has("--autotest")


static func read_autotest_name_from_command_line() -> String:
	var user_arguments: PackedStringArray = OS.get_cmdline_user_args()
	for argument_index in user_arguments.size():
		if user_arguments[argument_index] == "--autotest" and argument_index + 1 < user_arguments.size():
			return user_arguments[argument_index + 1]
	return ""


func run_named(test_name: String) -> int:
	if not _TEST_TYPES.has(test_name):
		push_error("Unknown autotest: %s" % test_name)
		return 1
	var test_type: Variant = _TEST_TYPES[test_name]
	return int(test_type.new().run())
