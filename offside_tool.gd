extends Control

## ============================================================
##  足球越位规则教学工具
##  功能：
##    - 22 个红/蓝球员（含守门员）均可拖拽
##    - 实时计算越位区域（半透明阴影）与越位线
##    - 标注处于越位位置的进攻方球员
## ============================================================

# ---------- 球员数据 ----------
# 每项: [team, x_norm, y_norm, is_gk, label]
# team: 0=红（进攻方）, 1=蓝（防守方）
# x_norm / y_norm: 0~1 归一化坐标
# is_gk: 是否守门员
var players: Array = []

# 当前拖拽的球员索引，-1 表示无
var dragging_idx: int = -1
var drag_offset: Vector2 = Vector2.ZERO

# ---------- 球场绘制区域（由 _draw 计算） ----------
var field_rect: Rect2 = Rect2()
var cell_size: float = 0.0  # 用于绘制球员圆点大小

# ---------- 颜色 ----------
const COLOR_RED: Color = Color(0.90, 0.15, 0.15)
const COLOR_RED_GK: Color = Color(0.95, 0.40, 0.15)
const COLOR_BLUE: Color = Color(0.15, 0.40, 0.90)
const COLOR_BLUE_GK: Color = Color(0.15, 0.75, 0.90)
const COLOR_FIELD: Color = Color(0.25, 0.55, 0.20)
const COLOR_LINE: Color = Color(1, 1, 1, 0.7)
const COLOR_SHADOW_RED: Color = Color(0.9, 0.2, 0.2, 0.25)
const COLOR_SHADOW_BLUE: Color = Color(0.2, 0.3, 0.9, 0.25)
const COLOR_OFFSIDE_LINE: Color = Color(1, 1, 0, 0.9)
const COLOR_TEXT: Color = Color(1, 1, 1)
const COLOR_GOAL: Color = Color(1, 1, 1, 0.8)

# ---------- 布局常量 ----------
const FIELD_MARGIN: float = 50.0
const TOP_BAR_HEIGHT: float = 60.0
const PLAYER_RADIUS: float = 12.0
const GK_RADIUS: float = 15.0
const HIT_RADIUS: float = 22.0  # 点击/拖拽的判定半径

# ---------- 状态 ----------
var offside_players: Array = []  # 当前处于越位位置的红队球员索引
var last_defender_idx: int = -1  # 最后第二名防守球员索引
var offside_line_x: float = -1.0  # 越位线 x（归一化）

# 球的位置（归一化坐标），初始在中圈
var ball_pos: Vector2 = Vector2(0.5, 0.5)
var dragging_ball: bool = false
var drag_ball_offset: Vector2 = Vector2.ZERO

# ============================================================
#  初始化
# ============================================================

func _ready() -> void:
	_init_players()
	queue_redraw()

func _init_players() -> void:
	players.clear()
	# —— 红队（进攻方，从左向右攻）11 人 ——
	# 守门员
	players.append([0, 0.04, 0.50, true, "GK"])
	# 后卫 4 人
	players.append([0, 0.18, 0.20, false, "RB"])
	players.append([0, 0.18, 0.40, false, "CB"])
	players.append([0, 0.18, 0.60, false, "CB"])
	players.append([0, 0.18, 0.80, false, "LB"])
	# 中场 4 人
	players.append([0, 0.35, 0.22, false, "RM"])
	players.append([0, 0.35, 0.42, false, "CM"])
	players.append([0, 0.35, 0.58, false, "CM"])
	players.append([0, 0.35, 0.78, false, "LM"])
	# 前锋 2 人
	players.append([0, 0.50, 0.35, false, "ST"])
	players.append([0, 0.50, 0.65, false, "ST"])

	# —— 蓝队（防守方）11 人 ——
	# 守门员
	players.append([1, 0.96, 0.50, true, "GK"])
	# 后卫 4 人
	players.append([1, 0.82, 0.20, false, "RB"])
	players.append([1, 0.82, 0.40, false, "CB"])
	players.append([1, 0.82, 0.60, false, "CB"])
	players.append([1, 0.82, 0.80, false, "LB"])
	# 中场 4 人
	players.append([1, 0.65, 0.22, false, "RM"])
	players.append([1, 0.65, 0.42, false, "CM"])
	players.append([1, 0.65, 0.58, false, "CM"])
	players.append([1, 0.65, 0.78, false, "LM"])
	# 前锋 2 人
	players.append([1, 0.52, 0.35, false, "ST"])
	players.append([1, 0.52, 0.65, false, "ST"])

# ============================================================
#  越位计算
# ============================================================

func _compute_offside() -> void:
	offside_players.clear()
	offside_line_x = -1.0
	last_defender_idx = -1

	# 收集蓝队（防守方）球员在右半场（x > 0.5）且按 x 从大到小排序
	var blues: Array = []  # [idx, x]
	for i in players.size():
		if players[i][0] == 1:
			blues.append([i, players[i][1]])
	# 按 x 降序（越靠近右侧球门越靠前）
	blues.sort_custom(func(a, b): return a[1] > b[1])

	if blues.size() < 2:
		return

	# 最后第二名防守球员（第二靠近右侧球门的）
	last_defender_idx = blues[1][0]
	var defender_x: float = players[last_defender_idx][1]
	# 越位线 = 最后第二名防守球员 与 球 中更靠近球门的那个（取更靠右的，即 max）
	# 因为球员必须比两者都更靠近球门才算越位
	offside_line_x = maxf(defender_x, ball_pos.x)
	# 越位只发生在对方半场
	offside_line_x = maxf(offside_line_x, 0.5)

	# 检查每个红队球员
	for i in players.size():
		if players[i][0] != 0:
			continue
		var p = players[i]
		# 条件1：在对方半场（x > 0.5）
		if p[1] <= 0.5:
			continue
		# 条件2：比最后第二名防守球员更靠近球门
		if p[1] <= defender_x:
			continue
		# 条件3：比球更靠近球门
		if p[1] <= ball_pos.x:
			continue
		offside_players.append(i)

# ============================================================
#  绘制
# ============================================================

func _draw() -> void:
	var size: Vector2 = get_size()
	var top_bar: float = TOP_BAR_HEIGHT
	var margin: float = FIELD_MARGIN

	# 计算球场区域（横屏适应，保持比例）
	var fw: float = size.x - margin * 2
	var fh: float = size.y - top_bar - margin * 2
	# 标准足球场宽长比约 0.68，这里取 0.65 便于显示
	var aspect: float = 0.65
	if fw * aspect > fh:
		# 高度受限
		var actual_h: float = fh
		var actual_w: float = fh / aspect
		field_rect = Rect2(
			(size.x - actual_w) / 2.0,
			top_bar + (fh - actual_h) / 2.0 + margin,
			actual_w, actual_h
		)
	else:
		var actual_w: float = fw
		var actual_h: float = fw * aspect
		field_rect = Rect2(
			margin,
			top_bar + (fh - actual_h) / 2.0 + margin,
			actual_w, actual_h
		)

	cell_size = field_rect.size.x / 100.0

	# ---- 1. 球场 ----
	_draw_field()

	# ---- 2. 越位阴影 ----
	_compute_offside()
	_draw_offside_shadow()

	# ---- 3. 越位线 ----
	_draw_offside_line()

	# ---- 4. 球员 ----
	_draw_players()

	# ---- 5. 顶部信息 ----
	_draw_top_info()

# ---------- 绘制球场 ----------

func _draw_field() -> void:
	var r: Rect2 = field_rect
	# 草地
	draw_rect(r, COLOR_FIELD)
	# 外边框
	draw_rect(r, COLOR_LINE, false, 2.0)

	# 中场线
	var mid_x: float = r.position.x + r.size.x / 2.0
	draw_line(Vector2(mid_x, r.position.y), Vector2(mid_x, r.position.y + r.size.y), COLOR_LINE, 1.5)

	# 中圈
	var center: Vector2 = Vector2(mid_x, r.position.y + r.size.y / 2.0)
	var circle_r: float = r.size.y * 0.15
	draw_arc(center, circle_r, 0, TAU, 64, COLOR_LINE, 1.5)

	# ---- 左罚球区（蓝队球门区） ----
	var pa_w: float = r.size.x * 0.15
	var pa_h: float = r.size.y * 0.40
	var pa_l: Rect2 = Rect2(r.position.x, r.position.y + (r.size.y - pa_h) / 2.0, pa_w, pa_h)
	draw_rect(pa_l, COLOR_LINE, false, 1.5)
	# 小罚球区
	var ga_w: float = r.size.x * 0.05
	var ga_h: float = r.size.y * 0.18
	var ga_l: Rect2 = Rect2(r.position.x, r.position.y + (r.size.y - ga_h) / 2.0, ga_w, ga_h)
	draw_rect(ga_l, COLOR_LINE, false, 1.5)

	# ---- 右罚球区（红队球门区） ----
	var pa_r: Rect2 = Rect2(r.position.x + r.size.x - pa_w, r.position.y + (r.size.y - pa_h) / 2.0, pa_w, pa_h)
	draw_rect(pa_r, COLOR_LINE, false, 1.5)
	var ga_r: Rect2 = Rect2(r.position.x + r.size.x - ga_w, r.position.y + (r.size.y - ga_h) / 2.0, ga_w, ga_h)
	draw_rect(ga_r, COLOR_LINE, false, 1.5)

	# ---- 球门 ----
	var goal_w: float = r.size.x * 0.025
	var goal_h: float = r.size.y * 0.22
	# 左球门（蓝队守门）
	var gl: Rect2 = Rect2(r.position.x - goal_w, r.position.y + (r.size.y - goal_h) / 2.0, goal_w, goal_h)
	draw_rect(gl, COLOR_GOAL)
	draw_rect(gl, COLOR_LINE, false, 1.0)
	# 右球门（红队守门）
	var gr: Rect2 = Rect2(r.position.x + r.size.x, r.position.y + (r.size.y - goal_h) / 2.0, goal_w, goal_h)
	draw_rect(gr, COLOR_GOAL)
	draw_rect(gr, COLOR_LINE, false, 1.0)

	# ---- 标注 ----
	# 半场文字
	var font_size: int = maxi(10, int(cell_size * 1.8))
	var font: Font = ThemeDB.fallback_font
	var font_size_actual: int = font_size
	draw_string(font, Vector2(r.position.x + r.size.x * 0.12, r.position.y + r.size.y * 0.06),
		"防守半场", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size_actual, COLOR_LINE)
	draw_string(font, Vector2(r.position.x + r.size.x * 0.62, r.position.y + r.size.y * 0.06),
		"进攻半场", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size_actual, COLOR_LINE)

	# 进攻方向箭头
	var arrow_y: float = r.position.y + r.size.y * 0.95
	var arrow_start: float = r.position.x + r.size.x * 0.05
	var arrow_end: float = r.position.x + r.size.x * 0.45
	draw_line(Vector2(arrow_start, arrow_y), Vector2(arrow_end, arrow_y), Color(1, 0.6, 0.2), 2.0)
	# 箭头头
	var arrow_tip: Vector2 = Vector2(arrow_end, arrow_y)
	draw_line(arrow_tip, Vector2(arrow_end - 8, arrow_y - 5), Color(1, 0.6, 0.2), 2.0)
	draw_line(arrow_tip, Vector2(arrow_end - 8, arrow_y + 5), Color(1, 0.6, 0.2), 2.0)
	draw_string(font, Vector2(arrow_start, arrow_y - 8), "进攻方向 →", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size_actual * 0.7, Color(1, 0.6, 0.2))

# ---------- 绘制越位阴影 ----------

func _draw_offside_shadow() -> void:
	if offside_line_x < 0:
		return

	var r: Rect2 = field_rect
	var line_screen_x: float = r.position.x + offside_line_x * r.size.x
	var right_edge: float = r.position.x + r.size.x

	# 阴影只覆盖对方半场（x > 0.5）
	var half_x: float = r.position.x + 0.5 * r.size.x
	var shadow_left: float = maxf(line_screen_x, half_x)
	if shadow_left >= right_edge:
		return

	var shadow_rect: Rect2 = Rect2(shadow_left, r.position.y, right_edge - shadow_left, r.size.y)

	# 使用红色半透明阴影（因为红队是进攻方）
	draw_rect(shadow_rect, COLOR_SHADOW_RED)

	# 添加斜线纹理效果（视觉提示）
	var step: float = 20.0
	var y_bottom: float = shadow_rect.position.y + shadow_rect.size.y
	var x_end: float = shadow_rect.position.x + shadow_rect.size.x
	for x_offset in range(0, int(shadow_rect.size.x) + int(step), int(step)):
		var x: float = shadow_rect.position.x + x_offset
		draw_line(
			Vector2(x, shadow_rect.position.y),
			Vector2(x - shadow_rect.size.x * 0.3, y_bottom),
			Color(1, 0, 0, 0.12), 1.0
		)

# ---------- 绘制越位线 ----------

func _draw_offside_line() -> void:
	if offside_line_x < 0:
		return
	var r: Rect2 = field_rect
	var sx: float = r.position.x + offside_line_x * r.size.x
	# 只在对方半场画越位线
	if sx < r.position.x + r.size.x * 0.5:
		return

	draw_line(
		Vector2(sx, r.position.y),
		Vector2(sx, r.position.y + r.size.y),
		COLOR_OFFSIDE_LINE, 2.5
	)

	# 标签
	var font: Font = ThemeDB.fallback_font
	var font_size: int = maxi(10, int(cell_size * 1.5))
	var label: String = "越位线"
	draw_string(font, Vector2(sx - 30, r.position.y + 15), label,
		HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, COLOR_OFFSIDE_LINE)

# ---------- 绘制球员 ----------

func _draw_players() -> void:
	var r: Rect2 = field_rect
	var font: Font = ThemeDB.fallback_font
	var font_size: int = maxi(8, int(cell_size * 1.2))

	for i in players.size():
		var p = players[i]
		var team: int = p[0]
		var nx: float = p[1]
		var ny: float = p[2]
		var is_gk: bool = p[3]
		var label: String = p[4]

		var cx: float = r.position.x + nx * r.size.x
		var cy: float = r.position.y + ny * r.size.y
		var radius: float = GK_RADIUS if is_gk else PLAYER_RADIUS

		# 颜色
		var color: Color
		if team == 0:
			color = COLOR_RED_GK if is_gk else COLOR_RED
		else:
			color = COLOR_BLUE_GK if is_gk else COLOR_BLUE

		# 如果处于越位位置，加发光边框
		var is_offside: bool = (i in offside_players)
		if is_offside:
			# 外发光
			draw_circle(Vector2(cx, cy), radius + 4, Color(1, 1, 0, 0.6))
			draw_circle(Vector2(cx, cy), radius + 2, Color(1, 1, 0, 0.4))

		# 球员圆点
		draw_circle(Vector2(cx, cy), radius, color)
		# 边框
		draw_circle(Vector2(cx, cy), radius, Color(1, 1, 1, 0.7), false, 1.5)

		# 守门员标记
		if is_gk:
			draw_circle(Vector2(cx, cy), radius * 0.4, Color(1, 1, 1, 0.6))

		# 标签（缩写）
		var team_prefix: String = "R-" if team == 0 else "B-"
		draw_string(font, Vector2(cx - radius, cy - radius - 4), team_prefix + label,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, COLOR_TEXT)

		# 如果是最后第二名防守球员，加标记
		if i == last_defender_idx:
			draw_string(font, Vector2(cx - 20, cy + radius + 14), "▼2nd",
				HORIZONTAL_ALIGNMENT_LEFT, -1, font_size * 0.7, COLOR_OFFSIDE_LINE)

	# ---- 绘制球 ----
	_draw_ball(r)

# ---------- 绘制顶部信息 ----------

func _draw_top_info() -> void:
	var size: Vector2 = get_size()
	var font: Font = ThemeDB.fallback_font
	var font_size: int = maxi(14, int(cell_size * 2.0))
	var small_font: int = maxi(10, int(cell_size * 1.4))

	var y: float = 12.0
	var x: float = 20.0

	# 标题
	draw_string(font, Vector2(x, y + font_size),
		"⚽ 足球越位规则教学工具",
		HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 1, 1))

	# 状态信息
	var info_x: float = size.x * 0.45
	var status_y: float = y + font_size

	if offside_players.size() > 0:
		var names: String = ""
		for idx in offside_players:
			names += "R-" + players[idx][4] + " "
		draw_string(font, Vector2(info_x, status_y),
			"⚠ 越位位置: " + names,
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(1, 0.8, 0))
	else:
		draw_string(font, Vector2(info_x, status_y),
			"✅ 无越位",
			HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.3, 1, 0.3))

	# 操作提示
	draw_string(font, Vector2(x, status_y + font_size + 6),
		"拖拽任意球员调整位置，实时观察越位区域变化",
		HORIZONTAL_ALIGNMENT_LEFT, -1, small_font, Color(0.7, 0.7, 0.7))

	# 图例
	var leg_x: float = size.x - 280.0
	var leg_y: float = y + 4
	draw_string(font, Vector2(leg_x, leg_y + small_font),
		"● 红队(攻)  ● 蓝队(守)  ⚽ 球", HORIZONTAL_ALIGNMENT_LEFT, -1, small_font, COLOR_TEXT)
	draw_string(font, Vector2(leg_x, leg_y + small_font * 2 + 4),
		"■ 越位阴影  ═ 越位线  [R] 重置", HORIZONTAL_ALIGNMENT_LEFT, -1, small_font, COLOR_TEXT)

# ============================================================
#  输入处理（拖拽）
# ============================================================

func _gui_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mb: InputEventMouseButton = event
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				# 查找点击的目标（优先球，再球员）
				var mp: Vector2 = mb.position
				var r: Rect2 = field_rect
				# 检查是否点击了球
				var bx: float = r.position.x + ball_pos.x * r.size.x
				var by: float = r.position.y + ball_pos.y * r.size.y
				if mp.distance_to(Vector2(bx, by)) <= HIT_RADIUS:
					dragging_ball = true
					drag_ball_offset = Vector2(mp.x - bx, mp.y - by)
					dragging_idx = -1
					accept_event()
					return
				# 检查是否点击了球员
				var idx: int = _hit_test_player(mp)
				if idx >= 0:
					dragging_idx = idx
					dragging_ball = false
					var p = players[idx]
					var px: float = r.position.x + p[1] * r.size.x
					var py: float = r.position.y + p[2] * r.size.y
					drag_offset = Vector2(mp.x - px, mp.y - py)
					accept_event()
			else:
				dragging_idx = -1
				dragging_ball = false

	elif event is InputEventMouseMotion:
		var mm: InputEventMouseMotion = event
		var mp: Vector2 = mm.position
		var r: Rect2 = field_rect
		
		if dragging_ball:
			var nx: float = (mp.x - drag_ball_offset.x - r.position.x) / r.size.x
			var ny: float = (mp.y - drag_ball_offset.y - r.position.y) / r.size.y
			nx = clampf(nx, 0.005, 0.995)
			ny = clampf(ny, 0.005, 0.995)
			ball_pos = Vector2(nx, ny)
			queue_redraw()
			accept_event()
		elif dragging_idx >= 0:
			var nx: float = (mp.x - drag_offset.x - r.position.x) / r.size.x
			var ny: float = (mp.y - drag_offset.y - r.position.y) / r.size.y
			nx = clampf(nx, 0.005, 0.995)
			ny = clampf(ny, 0.005, 0.995)
			players[dragging_idx][1] = nx
			players[dragging_idx][2] = ny
			queue_redraw()
			accept_event()

func _hit_test_player(mp: Vector2) -> int:
	var r: Rect2 = field_rect
	# 从上层到下层（后绘制的在上层），反向遍历
	for i in range(players.size() - 1, -1, -1):
		var p = players[i]
		var cx: float = r.position.x + p[1] * r.size.x
		var cy: float = r.position.y + p[2] * r.size.y
		var dist: float = mp.distance_to(Vector2(cx, cy))
		if dist <= HIT_RADIUS:
			return i
	return -1

# ============================================================
#  重置位置
# ============================================================

func _reset_positions() -> void:
	_init_players()
	queue_redraw()

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.keycode == KEY_R and event.pressed and not event.echo:
		_reset_positions()


# ---------- 绘制球 ----------

func _draw_ball(r: Rect2) -> void:
	var bx: float = r.position.x + ball_pos.x * r.size.x
	var by: float = r.position.y + ball_pos.y * r.size.y
	var radius: float = PLAYER_RADIUS * 0.7
	
	# 阴影
	draw_circle(Vector2(bx + 1, by + 1), radius, Color(0, 0, 0, 0.3))
	# 球体（白色）
	draw_circle(Vector2(bx, by), radius, Color(1, 1, 1))
	# 边框
	draw_circle(Vector2(bx, by), radius, Color(0.3, 0.3, 0.3), false, 1.5)
	# 球标记 "⚽"
	var font: Font = ThemeDB.fallback_font
	var font_size: int = maxi(8, int(cell_size * 1.5))
	draw_string(font, Vector2(bx - radius * 0.5, by + font_size * 0.35),
		"⚽", HORIZONTAL_ALIGNMENT_LEFT, -1, font_size, Color(0.8, 0.6, 0.2))
