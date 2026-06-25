extends RefCounted

## 越位教学工具自动化测试
## 验证 22 名球员初始化、越位计算、拖拽交互等核心功能

static func run(scene_tree: SceneTree) -> void:
	print("=== OffsideTest: 开始 ===")
	
	# 加载主场景
	var main_scene = load("res://main.tscn")
	var main = main_scene.instantiate()
	scene_tree.root.add_child(main)
	# 手动确保初始化（_ready 可能还没被调用）
	main._init_players()
	
	assert(main != null, "Main 节点应存在")
	
	# ---- 测试1: 22名球员初始化 ----
	_test_player_count(main)
	
	# ---- 测试2: 红蓝各11人 ----
	_test_team_counts(main)
	
	# ---- 测试3: 2名守门员 ----
	_test_goalkeepers(main)
	
	# ---- 测试4: 初始越位计算 ----
	_test_initial_offside(main)
	
	# ---- 测试5: 拖拽后越位检测 ----
	_test_drag_updates_offside(main)
	
	# ---- 测试6: 越位阴影区域逻辑 ----
	_test_offside_shadow_logic(main)
	
	# ---- 测试7: 重置功能 ----
	_test_reset(main)
	
	# 清理
	scene_tree.root.remove_child(main)
	main.queue_free()
	
	print("=== OffsideTest: 全部通过 ===")
	scene_tree.quit(0)

static func _test_player_count(main: Control) -> void:
	var count = main.players.size()
	assert(count == 22, "应有 22 名球员，实际 %d" % count)
	print("  [PASS] 球员总数: 22")

static func _test_team_counts(main: Control) -> void:
	var red = 0
	var blue = 0
	for p in main.players:
		if p[0] == 0:
			red += 1
		else:
			blue += 1
	assert(red == 11, "红队应有 11 人，实际 %d" % red)
	assert(blue == 11, "蓝队应有 11 人，实际 %d" % blue)
	print("  [PASS] 红队 %d 人, 蓝队 %d 人" % [red, blue])

static func _test_goalkeepers(main: Control) -> void:
	var gk = 0
	for p in main.players:
		if p[3]:
			gk += 1
	assert(gk == 2, "应有 2 名守门员，实际 %d" % gk)
	print("  [PASS] 守门员: 2")

static func _test_initial_offside(main: Control) -> void:
	main._compute_offside()
	var offside_count = main.offside_players.size()
	assert(offside_count == 0, "初始状态不应有越位，实际 %d" % offside_count)
	print("  [PASS] 初始越位数: 0")

static func _test_drag_updates_offside(main: Control) -> void:
	var old_x = main.players[10][1]
	main.players[10][1] = 0.92
	main._compute_offside()
	
	assert(main.offside_players.size() > 0, "前锋移到 x=0.92 后应触发越位")
	assert(10 in main.offside_players, "索引10 应标记为越位")
	print("  [PASS] 拖拽后越位检测: 索引10 越位 (x=0.92, 越位线=%.3f)" % main.offside_line_x)
	
	main.players[10][1] = old_x
	main._compute_offside()
	assert(not (10 in main.offside_players), "恢复后索引10 不应越位")
	print("  [PASS] 恢复位置后越位消除")

static func _test_offside_shadow_logic(main: Control) -> void:
	# 测试1：把蓝队守门员往前移，验证越位线变化
	var gk_idx = 11  # 蓝队守门员（索引11）
	var old_gk_x = main.players[gk_idx][1]
	main.players[gk_idx][1] = 0.75  # 守门员前移
	main._compute_offside()
	var line_with_gk_forward = main.offside_line_x
	# 守门员前移后，最后第二名防守球员应该更靠前
	assert(line_with_gk_forward > 0.5, "守门员前移后越位线应仍在右半场: %.3f" % line_with_gk_forward)
	print("  [PASS] 守门员前移 (x=0.75) → 越位线=%.3f" % line_with_gk_forward)
	
	# 测试2：把所有蓝队球员移到左半场，验证无进攻球员越位
	var old_positions = []
	for i in range(11, 22):
		old_positions.append([main.players[i][1], main.players[i][2]])
		main.players[i][1] = 0.2 + (i - 11) * 0.02
	main._compute_offside()
	assert(main.offside_players.size() == 0, "蓝队全在左半场时不应有红队越位")
	assert(main.offside_line_x >= 0.5, "蓝队全在左半场时越位线应为 0.5: %.3f" % main.offside_line_x)
	print("  [PASS] 蓝队全在左半场 → 无越位 (越位线=%.3f)" % main.offside_line_x)
	
	# 恢复
	main._reset_positions()
	
	# 测试3：球比防守球员更靠后时，越位线 = max(防守, 球) = 防守
	main.ball_pos.x = 0.55
	var old_def_positions = []
	for i in range(12, 16):
		old_def_positions.append(main.players[i][1])
		main.players[i][1] = 0.7
	main._compute_offside()
	assert(abs(main.offside_line_x - 0.7) < 0.01, "球在防守球员后时越位线应为防守球员位置 0.7: %.3f" % main.offside_line_x)
	print("  [PASS] 球(x=0.55)在防守球员(x=0.7)后 → 越位线=0.700 (max)")
	
	# 测试4：球比防守球员更靠前时，越位线 = max(防守, 球) = 球
	main.ball_pos.x = 0.85
	main._compute_offside()
	assert(abs(main.offside_line_x - 0.85) < 0.01, "球在防守球员前时越位线应为球位置 0.85: %.3f" % main.offside_line_x)
	print("  [PASS] 球(x=0.85)在防守球员(x=0.7)前 → 越位线=0.850 (球)")
	
	# 测试5：球在 0.85，防守在 0.7，前锋在 0.8 → 不应越位（在球后）
	var old_st_x = main.players[9][1]
	main.players[9][1] = 0.8
	main._compute_offside()
	assert(not (9 in main.offside_players), "前锋 x=0.8 在球 x=0.85 后 → 不应越位")
	print("  [PASS] 前锋(x=0.8) < 球(x=0.85) → 不越位")
	
	# 测试6：双前锋同时在防守和球前面 → 越位
	main.players[10][1] = 0.95
	main.players[9][1] = 0.95
	main._compute_offside()
	assert(10 in main.offside_players and 9 in main.offside_players, "双前锋 > 越位线 → 应越位")
	print("  [PASS] 双前锋(x=0.95) > 越位线(0.85) → 越位")
	
	# 恢复
	main.ball_pos.x = 0.5
	main.players[9][1] = old_st_x
	main.players[10][1] = 0.5
	for i in range(4):
		main.players[12 + i][1] = old_def_positions[i]
	main._reset_positions()
	print("  [PASS] 越位阴影逻辑综合测试通过")

static func _test_reset(main: Control) -> void:
	main.players[0][1] = 0.5
	main.players[1][1] = 0.6
	main._reset_positions()
	assert(main.players[0][1] < 0.1, "守门员重置后应在球门附近: %.3f" % main.players[0][1])
	print("  [PASS] 重置功能正常")
