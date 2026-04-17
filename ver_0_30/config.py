#若连续跳跃建造时漏放方块请尝试调整JUMP_PUT_WAIT或将BUILD_RESET_EVERY_N_BLOCKS设为1
# =========================
#  基础控制参数
# =========================
TURNBACKSTEP = 13               # 转身步数校准参数（自动校准覆盖）
METER = 0.25                    # 单格前进时长（自动校准覆盖）
LEFTCLICKTIME = 0.6             # 左键点击持续时间(自动校准覆盖)
RESET_WAIT = 0.08               # 视角 reset 后的等待时间
MOVE_WAIT = 0.10                # 移动按键后等待时间

# =========================
#  鼠标与动作参数
# =========================
JUMP_PUT_WAIT = 0.08                # 跳跃后放置方块的等待时间（自动校准覆盖）
RIGHTCLICKTIME = 0.15               # 右键点击持续时间
BREAK_PRESS_TIME = 0.15             # 挖掘持续时间
BLOCK_PLACE_INTERVAL = 0.08         # 放置方块的时间间隔
BLOCK_BREAK_INTERVAL = 0.08         # 挖掘动作的时间间隔
COLUMN_ACTION_INTERVAL = 0.03       # 建造柱子动作间的时间间隔
COLUMN_FINISH_WAIT = 0.05           # 柱子建造完成后的等待时间

# =========================
#  动作比例参数
# =========================
LOOK_DOWN_JUMP_PUT_RATIO = 0.6      # 跳搭时低头角度比例（基于 TURNBACKSTEP）
BREAK_RATIO = 0.4                   # 挖上一柱时的低头角度比例
BREAK_WHOLE_COLUMN_LOOK_DOWN_RATIO = 0.6  # 拆整柱时的低头角度比例

# =========================
#  鼠标底层参数
# =========================
MOUSE_FRAME = 0.016                 # 每帧鼠标响应时间
MOUSE_STEP = 30                     # 鼠标步移动单位

# =========================
#  启动与停止控制
# =========================
START_DELAY_SECONDS = 5             # 校准启动前的延迟时间

# =========================
#  工具栏快捷键
# =========================
DEADLYPICK = '2'                    # 快捷键：死亡镐
STONE = '8'                         # 快捷键：石块

# =========================
#  导航优化参数
# =========================
LONG_MOVE_RENORMALIZE_EVERY = 3     # 长距离移动时，每隔多少步重新校准
LONG_MOVE_RESET_EVERY = 3           # 长距离移动时，每隔多少步强制 reset
LONG_MOVE_FORCE_RESET_MAX = 6       # 长距离移动时，偏差超过最大步数时强制校正

# =========================
#  建造行为优化参数
# =========================
BUILD_RESET_EVERY_N_BLOCKS = 3      # 建造过程中的 reset 频率
BREAK_RESET_EVERY_N_BLOCKS = 3      # 挖掘过程中的 reset 频率

# =========================
# 读取与状态校验相关参数
# =========================
READ_RETRY_TIMES = 3        # 最大读取重试次数
READ_RETRY_INTERVAL = 0.08  # 读取重试时间间隔（单位：秒）

# =========================
#  读取与状态校验相关参数
# =========================
GRID_CENTER_TOLERANCE = 0.20  # 用于判断玩家是否在网格中心点的容差（单位：格）
FACE_TOLERANCE = 0.01         # 用于判断视角是否对齐的容差(没有实装)

#=======?=======
JUMP_PUT_POST_CLICK_WAIT = 0.08
COLUMN_FINAL_PLACE_SETTLE_WAIT = 0.20
SLEEP_BETWEEN_COLUMNS = 0.0
SLEEP_BETWEEN_ROWS = 0.0
