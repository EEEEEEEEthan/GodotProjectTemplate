extends Node

var command := "ping"

func _ready():
	GameMcp.register_handle(self)

func on_receive(data: Dictionary, return_callback: Callable) -> void:
	return_callback.call({
		"pong": true,
		"received": data,
	})
