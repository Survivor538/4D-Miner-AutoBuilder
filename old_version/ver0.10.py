#第一代4D Miner自动建造奴隶ver0.10
#可以在平坦地形上自动建造任意尺寸的超长方体
#4D Miner版本0.2.1.4 alpha

import time
import ctypes
import pyautogui

# =========================
# 预设参数
# =========================

#TURNBACKSTEP为使用look_right(TURNBACKSTEP)时使人物视角大致转向背后的值(180°)，可能与鼠标灵敏度有关，请用主程序中被注释掉的程序进行试验以确认具体数值
TURNBACKSTEP = 13
#METER为使用move_forward(METER)时使人物向前移动约1格时的值
METER = 0.25

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
        send_mouse(0, 0, LEFTDOWN)
        time.sleep(0.08)
        send_mouse(0, 0, LEFTUP)
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

    def __init__(self):
        self.c = Controller()

    def putforward(self):
        self.c.look_down(int(TURNBACKSTEP*0.25))
        self.c.right_click()
        self.c.look_up(int(TURNBACKSTEP*0.25))
        
    def putback(self):
        self.c.look_right(TURNBACKSTEP)
        self.c.look_down(int(TURNBACKSTEP*0.25))
        self.c.right_click()
        self.c.look_up(int(TURNBACKSTEP*0.25))
        self.c.look_left(TURNBACKSTEP)

    def jumpput(self):
        self.c.reset_view_ctrlzx()
        self.c.look_down(int(TURNBACKSTEP * 0.6))
        time.sleep(0.1)
        pyautogui.keyDown('space')
        time.sleep(0.05)
        pyautogui.keyUp('space')
        self.c.right_click()
        self.c.look_up(int(TURNBACKSTEP * 0.6))
        time.sleep(0.5)
        
    def build_line_plusZ(self, n):        
        self.c.reset_view_ctrlzx()
        if n <= 3:
            for i in range(n):
                self.jumpput()
                if i < n - 1:
                    self.c.move_forward(METER)
            return
        for i in range(n):            
            if i == 0:
                self.jumpput()
                self.c.move_forward(METER)
            elif i == n - 2:
                self.c.reset_view_ctrlzx()            
                self.putback()
            elif i == n - 1:
                self.jumpput()
            else:
                self.c.move_forward(METER)
                self.c.reset_view_ctrlzx()            
                self.putback()
                
    def build_line_minusZ(self, n):        
        self.c.reset_view_ctrlzx()
        if n <= 3:
            for i in range(n):
                self.jumpput()
                if i < n - 1:
                    self.c.move_back(METER)
            return
        for i in range(n):            
            if i == 0:
                self.jumpput()
                self.c.move_back(METER)
            elif i == n - 2:
                self.c.reset_view_ctrlzx()            
                self.putforward()
            elif i == n - 1:
                self.jumpput()
            else:
                self.c.move_back(METER)
                self.c.reset_view_ctrlzx()            
                self.putforward()

    def build_plane(self, width, depth):
        """
        width = X方向（行数）
        depth = Z方向（每行长度）
        """
        for x in range(width):
            
            if x % 2 == 0:
                self.build_line_plusZ(depth)
            else:
                self.build_line_minusZ(depth)

            if x < width - 1:
                    self.c.move_left(METER)

    def return_to_layer_origin(self, width, depth):
        self.c.reset_view_ctrlzx()
        self.c.move_long_minusX(width-1)
        self.c.reset_view_ctrlzx()
        if width % 2 == 1:
            self.c.move_long_minusZ(depth-1)

    def build_3d(self, width, depth, height):
        for h in range(height):
            self.build_plane(width, depth)
            self.return_to_layer_origin(width,depth)

    def plus_W(self):
        self.c.reset_view_ctrlzw()
        self.c.move_left()
        self.c.reset_view_ctrlzx()

    def build_4d(self, width, depth, height, w_layers):
        for w in range(w_layers):
            self.build_3d(width, depth, height)
            if w < w_layers-1:
                self.plus_W()

# =========================
# 主程序
# =========================

if __name__ == "__main__":

    print("请确认TURNBACKSTEP数值已调整为合适的值")
    print("本程序可以在平坦地形上自动建造4d超长方体，请手拿物块，站在想要建造的超长方体的x,y,z,w的最小坐标处，建造过程中不要使用鼠标或键盘")
    width = int(input("请输入x方向的长度："))
    height = int(input("请输入y方向的长度："))
    depth = int(input("请输入z方向的长度："))
    w_layers = int(input("请输入w方向的长度："))
    
    print("5秒后开始，请切换到游戏窗口")
    time.sleep(5)

    b = Builder()
    b.build_4d(width,depth,height,w_layers)

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
