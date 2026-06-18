extends Node

const GameMcpDemoHandlerScript := preload("res://main/game_mcp_demo_handler.gd")


func _ready() -> void:
	GameMcp.register_handle(GameMcpDemoHandlerScript.new())
