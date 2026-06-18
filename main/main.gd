extends Node

const Test = preload("res://tests/test.gd")


func _ready() -> void:
	if not Test.has_autotest_argument():
		return
	var test_name: String = Test.read_autotest_name_from_command_line()
	if test_name.is_empty():
		push_error("Missing test name after --autotest")
		get_tree().quit(1)
		return
	var exit_code: int = Test.new().run_named(test_name)
	get_tree().quit(exit_code)
