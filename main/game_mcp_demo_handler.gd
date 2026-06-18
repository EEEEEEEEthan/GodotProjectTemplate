extends RefCounted

var command := "ping"


func on_receive(data: Dictionary, return_callback: Callable) -> void:
	return_callback.call({
		"pong": true,
		"received": data,
	})
