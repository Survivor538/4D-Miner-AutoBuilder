#第一代4D Miner自动建造奴隶ver0.20
#可以在平坦地形上自动建造任意形状的建筑
#4D Miner版本0.2.1.4 alpha

import time
import ctypes
import pyautogui
import keyboard

# =========================
# 预设参数
# =========================

#TURNBACKSTEP为使用look_right(TURNBACKSTEP)时使人物视角大致转向背后的值(180°)，可能与鼠标灵敏度有关，请用主程序中被注释掉的程序进行试验以确认具体数值
TURNBACKSTEP = 13
#METER为使用move_forward(METER)时使人物向前移动约1格时的值
METER = 0.25
#用于left_click挖掉一个方块的时间
LEFTCLICKTIME = 0.6
#物品栏
DEADLYPICK = '2'
STONE = '8'

# =========================
# 结构输入
# =========================
def generate_structure():
    s = set()

    '''
    # 示例：空心立方体
    for x in range(5):
        for y in range(5):
            for z in range(5):
                for w in range(5):
                    if x in [0,4] or y in [0,4] or z in [0,4] or w in [0,4]:
                        s.add((x,y,z,w))
    '''

    #4d球壳
    R = 5
    center = R

    for x in range(2*R+1):
        for y in range(2*R+1):
            for z in range(2*R+1):
                for w in range(2*R+1):

                    dx = x - center
                    dy = y - center
                    dz = z - center
                    dw = w - center

                    d2 = dx*dx + dy*dy + dz*dz + dw*dw

                    if R*R - 2 <= d2 <= R*R + 2:
                        s.add((x, y, z, w))
    return s

# =========================
# 停止功能(并不十分有效)
# =========================
STOP_FLAG = False

def check_stop():
    global STOP_FLAG
    if keyboard.is_pressed('i'):  # 按i停止
        STOP_FLAG = True

# =========================
# Windows SendInput
# =========================

PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL)
    ]

class INPUT_I(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", INPUT_I)]

INPUT_MOUSE = 0

MOUSE_MOVE = 0x0001
LEFTDOWN = 0x0002
LEFTUP = 0x0004
RIGHTDOWN = 0x0008
RIGHTUP = 0x0010


def send_mouse(dx=0, dy=0, flags=MOUSE_MOVE):
    extra = ctypes.c_ulong(0)
    ii = INPUT_I()
    ii.mi = MOUSEINPUT(dx, dy, 0, flags, 0, ctypes.pointer(extra))
    cmd = INPUT(INPUT_MOUSE, ii)
    ctypes.windll.user32.SendInput(1, ctypes.pointer(cmd), ctypes.sizeof(cmd))

# =========================
# 控制器
# =========================

class Controller:

    # 统一参数
    FRAME = 0.016
    STEP = 30

    # =========================
    # 转向
    # =========================

    def look_right(self, steps=TURNBACKSTEP):
        for _ in range(steps):
            send_mouse(self.STEP, 0, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_left(self, steps=TURNBACKSTEP):
        for _ in range(steps):
            send_mouse(-self.STEP, 0, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_up(self, steps=TURNBACKSTEP):
        for _ in range(steps):
            send_mouse(0, -self.STEP, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_down(self, steps=TURNBACKSTEP):
        for _ in range(steps):
            send_mouse(0, self.STEP, MOUSE_MOVE)
            time.sleep(self.FRAME)

    # =========================
    # 点击
    # =========================

    def right_click(self):
        send_mouse(0, 0, RIGHTDOWN)
        time.sleep(0.08)
        send_mouse(0, 0, RIGHTUP)
        time.sleep(0.05)

    def left_click(self):
        #挖掉一个方块
        pyautogui.press(DEADLYPICK)
        time.sleep(0.05)

        send_mouse(0, 0, LEFTDOWN)
        time.sleep(LEFTCLICKTIME)
        send_mouse(0, 0, LEFTUP)
        time.sleep(0.05)

        pyautogui.press(STONE)
        time.sleep(0.05)
        
    # =========================
    # 移动
    # =========================

    def move_forward(self, t=METER):
        pyautogui.keyDown('w')
        time.sleep(t)
        pyautogui.keyUp('w')
        time.sleep(0.05)
        
    def move_back(self, t=METER):
        pyautogui.keyDown('s')
        time.sleep(t)
        pyautogui.keyUp('s')
        time.sleep(0.05)

    def move_left(self, t=METER):
        pyautogui.keyDown('a')
        time.sleep(t)
        pyautogui.keyUp('a')
        time.sleep(0.05)

    def move_right(self, t=METER):
        pyautogui.keyDown('d')
        time.sleep(t)
        pyautogui.keyUp('d')
        time.sleep(0.05)

    def move_jump(self):
        pyautogui.keyDown('space')
        time.sleep(0.05)
        pyautogui.keyUp('space')
        time.sleep(0.05)

    def move_long_plusZ(self, steps):
        for i in range(steps):
            if i % 2 == 0:
                self.reset_view_ctrlzx()
            self.move_forward(METER)
            time.sleep(0.1)

    def move_long_minusZ(self, steps):
        for i in range(steps):
            if i % 2 == 0:
                self.reset_view_ctrlzx()
            self.move_back(METER)
            time.sleep(0.1)

    def move_long_plusX(self, steps):
        for i in range(steps):
            if i % 2 == 0:
                self.reset_view_ctrlzx()
            self.move_left(METER)
            time.sleep(0.1)

    def move_long_minusX(self, steps):
        for i in range(steps):
            if i % 2 == 0:
                self.reset_view_ctrlzx()
            self.move_right(METER)
            time.sleep(0.1)

    def move_plusW(self):
        self.reset_view_ctrlzw()
        self.move_left(METER)
        self.reset_view_ctrlzx()

    def move_minusW(self):
        self.reset_view_ctrlzw()
        self.move_right(METER)
        self.reset_view_ctrlzx()

    def jump_put(self):
        self.reset_view_ctrlzx()
        self.look_down(int(TURNBACKSTEP * 0.6))
        time.sleep(0.1)
        pyautogui.keyDown('space')
        time.sleep(0.05)
        pyautogui.keyUp('space')
        self.right_click()
        self.look_up(int(TURNBACKSTEP * 0.6))
        time.sleep(0.5)

    # =========================
    # 视角重置
    # =========================

    def reset_view_ctrlzx(self):
        pyautogui.keyDown('ctrl')
        pyautogui.keyDown('z')
        pyautogui.press('x')
        pyautogui.keyUp('z')
        pyautogui.keyUp('ctrl')
        time.sleep(0.08)

    def reset_view_ctrlzw(self):
        pyautogui.keyDown('ctrl')
        pyautogui.keyDown('z')
        pyautogui.press('w')
        pyautogui.keyUp('z')
        pyautogui.keyUp('ctrl')
        time.sleep(0.08)

    def reset_view_ctrlwx(self):
        pyautogui.keyDown('ctrl')
        pyautogui.keyDown('w')
        pyautogui.press('x')
        pyautogui.keyUp('w')
        pyautogui.keyUp('ctrl')
        time.sleep(0.08)

# =========================
# 建造逻辑
# =========================

class Builder:

    def __init__(self, structure):
        self.c = Controller()
        self.structure = structure

        self.cur_x = 0
        self.cur_y = 0
        self.cur_z = 0
        self.cur_w = 0

        self.max_y = max(p[1] for p in structure) + 1

    def move_to_column(self, x, z, w):

        dx = x - self.cur_x
        dz = z - self.cur_z
        dw = w - self.cur_w

        for _ in range(abs(dw)):
            if dw > 0:
                self.c.move_plusW()
            else:
                self.c.move_minusW()

        if dx > 0:
            self.c.move_long_plusX(dx)
        else:
            self.c.move_long_minusX(-dx)

        if dz > 0:
            self.c.move_long_plusZ(dz)
        else:
            self.c.move_long_minusZ(-dz)

        self.cur_x = x
        self.cur_z = z
        self.cur_w = w

    def is_prev_column_dirty(self, x, z, w, y):

        if z == 0:
            return False    

        if (x, y, z-1, w) not in self.structure:
            return True

        return False

    def build_column(self, x, z, w):

        for y in range(self.max_y):            

            if self.is_prev_column_dirty(x, z, w, y):
                self.c.reset_view_ctrlzx()
                self.c.look_right(TURNBACKSTEP)
                self.c.look_down(int(TURNBACKSTEP*0.4))
                self.c.left_click()
                self.c.reset_view_ctrlzx()

            self.c.jump_put()

            check_stop()
            if STOP_FLAG:
                return


    def break_whole_column(self):

        for y in range(self.max_y):
            self.c.reset_view_ctrlzx()
            self.c.look_down(int(TURNBACKSTEP*0.6))
            self.c.left_click()
            
    
    def build_all(self):

        pyautogui.press(STONE)
        time.sleep(0.05)

        xs = [p[0] for p in self.structure]
        ys = [p[1] for p in self.structure]
        zs = [p[2] for p in self.structure]
        ws = [p[3] for p in self.structure]

        max_x = max(xs)
        max_z = max(zs)
        max_w = max(ws)

        for w in range(max_w + 1):
            for x in range(max_x + 1):
                for z in range(max_z + 2):      #z方向上多建一个辅助柱

                    check_stop()
                    if STOP_FLAG:
                        return
                    
                    self.move_to_column(x, z, w)
                    self.build_column(x, z, w)

                    if z == max_z + 1:
                        self.break_whole_column()
                            
# =========================
# 主程序
# =========================
    
if __name__ == "__main__":

    print("请确认TURNBACKSTEP数值已调整为合适的值")
    print("本程序可以在平坦地形上自动建造设定好的建筑，请站在建筑的x,y,z,w的最小坐标处，建造过程中不要使用鼠标或键盘")
    print("请将物块放置于物品栏第8格，死亡镐置于物品栏第2格，并注意物块的量需要足够多")
    print("如果想终止程序可以尝试不断按‘i’，但可能并不十分有效")
    input("按下回车键开始")
    
    print("5秒后开始，请切换到游戏窗口")
    time.sleep(5)
    
    structure = generate_structure()

    b = Builder(structure)

    b.build_all()

    print("完成")


    """
    #正式使用前请使用此程序确认TURNBACKSTEP的值
    #不断修改程序开头时的TURNBACKSTEP，以求达到此验证程序运行时使人物的视角向后约转动180度的效果

    print("现在运行的是验证程序")
    print("5秒后开始，请切换到游戏窗口")
    time.sleep(5)
    
    b = Builder()
    b.c.reset_view_ctrlzx()
    b.c.look_right(TURNBACKSTEP)

    print("完成，期待的结果是facing direction中z为-1.0")
    """

