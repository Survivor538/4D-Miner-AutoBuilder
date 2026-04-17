import threading

try:
    import keyboard
except ImportError:
    keyboard = None

class StopController:
    def __init__(self, hotkey="f8"):
        self.hotkey = hotkey
        self._stop_event = threading.Event()
        self._started = False

    def start(self):
        if self._started:
            return
        self._started = True

        if keyboard is None:
            print("[stop_control] keyboard 未安装，热键停止不可用")
            print("[stop_control] 请先执行: pip install keyboard")
            return

        keyboard.add_hotkey(self.hotkey, self.request_stop)
        print(f"[stop_control] 已注册停止热键: {self.hotkey}")

    def request_stop(self):
        if not self._stop_event.is_set():
            self._stop_event.set()
            print("\n[stop_control] 收到停止请求，将在安全点停止...")

    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    def clear(self):
        self._stop_event.clear()

    def shutdown(self):
        if keyboard is not None:
            try:
                keyboard.unhook_all_hotkeys()
            except Exception:
                pass
