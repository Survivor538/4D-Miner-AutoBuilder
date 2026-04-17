import time
import ctypes
import pyautogui

from config import (
    LEFTCLICKTIME,
    DEADLYPICK,
    STONE,
    RESET_WAIT,
    MOUSE_FRAME,
    MOUSE_STEP,
)
from runtime_params import build_runtime_params

# =========================
# Windows SendInput 鼠标封装
# =========================

PUL = ctypes.POINTER(ctypes.c_ulong)

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
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

class Controller:
    FRAME = MOUSE_FRAME
    STEP = MOUSE_STEP

    def __init__(self, runtime_params=None):
        if runtime_params is None:
            runtime_params = build_runtime_params()

        self.runtime_params = runtime_params
        self.turnbackstep = runtime_params.turnbackstep
        self.meter = runtime_params.meter

    # =========================
    # 视角控制
    # =========================
    def look_right(self, steps=None):
        if steps is None:
            steps = self.turnbackstep
        for _ in range(steps):
            send_mouse(self.STEP, 0, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_left(self, steps=None):
        if steps is None:
            steps = self.turnbackstep
        for _ in range(steps):
            send_mouse(-self.STEP, 0, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_up(self, steps=None):
        if steps is None:
            steps = self.turnbackstep
        for _ in range(steps):
            send_mouse(0, -self.STEP, MOUSE_MOVE)
            time.sleep(self.FRAME)

    def look_down(self, steps=None):
        if steps is None:
            steps = self.turnbackstep
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

    def left_click(self, duration=LEFTCLICKTIME):
        send_mouse(0, 0, LEFTDOWN)
        time.sleep(duration)
        send_mouse(0, 0, LEFTUP)
        time.sleep(0.05)

    # =========================
    # 物品切换
    # =========================
    def select_block(self):
        pyautogui.press(STONE)
        time.sleep(0.05)

    def select_pickaxe(self):
        pyautogui.press(DEADLYPICK)
        time.sleep(0.05)

    # =========================
    # 基础动作
    # =========================
    def jump(self):
        pyautogui.keyDown("space")
        time.sleep(0.05)
        pyautogui.keyUp("space")
        time.sleep(0.05)

    def move_forward(self, t=None):
        if t is None:
            t = self.meter
        pyautogui.keyDown("w")
        time.sleep(t)
        pyautogui.keyUp("w")
        time.sleep(0.05)

    def move_back(self, t=None):
        if t is None:
            t = self.meter
        pyautogui.keyDown("s")
        time.sleep(t)
        pyautogui.keyUp("s")
        time.sleep(0.05)

    def move_left(self, t=None):
        if t is None:
            t = self.meter
        pyautogui.keyDown("a")
        time.sleep(t)
        pyautogui.keyUp("a")
        time.sleep(0.05)

    def move_right(self, t=None):
        if t is None:
            t = self.meter
        pyautogui.keyDown("d")
        time.sleep(t)
        pyautogui.keyUp("d")
        time.sleep(0.05)

    # =========================
    # 视角重置
    # =========================
    def reset_view_ctrlzx(self):
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("z")
        pyautogui.press("x")
        pyautogui.keyUp("z")
        pyautogui.keyUp("ctrl")
        time.sleep(RESET_WAIT)

    def reset_view_ctrlzw(self):
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("z")
        pyautogui.press("w")
        pyautogui.keyUp("z")
        pyautogui.keyUp("ctrl")
        time.sleep(RESET_WAIT)

    def reset_view_ctrlwx(self):
        pyautogui.keyDown("ctrl")
        pyautogui.keyDown("w")
        pyautogui.press("x")
        pyautogui.keyUp("w")
        pyautogui.keyUp("ctrl")
        time.sleep(RESET_WAIT)
