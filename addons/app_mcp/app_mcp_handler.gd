class_name ApplicationMcpHandler
extends RefCounted
## 协议回调基类；子类实现 on_receive 并设置 command。


var command: String


func _init(handler_command: String = "") -> void:
	command = handler_command


func on_receive(command: String, data: Dictionary, return_callback: Callable) -> void:
	return_callback.call({})
