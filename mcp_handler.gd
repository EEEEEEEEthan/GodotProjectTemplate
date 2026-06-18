extends Node

var command := "ping"

func _ready():
	MCP.register_handle(self)

func on_receive(data: Dictionary, return_callback: Callable) -> void:
	match data.get(&"command"):
		&"ping":
			return_callback.call({"pong": true,})
