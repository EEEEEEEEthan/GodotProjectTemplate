extends Node

func _ready():
	add_child(ApplicationMcp.new(on_receive))

func on_receive(command: String, data: Dictionary, response: Callable) -> void:
	match command:
		&"ping":
			response.call({&"pong": true})
