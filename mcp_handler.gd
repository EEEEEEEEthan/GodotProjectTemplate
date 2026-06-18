extends Node

var command := "ping"

func _ready():
	MCP.register_handle(self)

func on_receive(command: String, data: Dictionary, return_callback: Callable) -> void:
	match command:
		"ping":
			return_callback.call({"pong": true})
