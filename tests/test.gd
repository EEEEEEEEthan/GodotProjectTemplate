class_name Test
extends RefCounted

const HelloTest = preload("res://tests/hello_test.gd")

const _TEST_TYPES: Dictionary = {
	"hellotest": HelloTest,
}


static func has_autotest_argument() -> bool:
	var command_line_arguments: PackedStringArray = OS.get_cmdline_args()
	return command_line_arguments.has("--autotest")


static func read_autotest_name_from_command_line() -> String:
	var command_line_arguments: PackedStringArray = OS.get_cmdline_args()
	for argument_index in command_line_arguments.size():
		if command_line_arguments[argument_index] == "--autotest" and argument_index + 1 < command_line_arguments.size():
			return command_line_arguments[argument_index + 1]
	return ""


func run_named(test_name: String) -> int:
	if not _TEST_TYPES.has(test_name):
		push_error("Unknown autotest: %s" % test_name)
		return 1
	var test_type: Variant = _TEST_TYPES[test_name]
	return int(test_type.new().run())
