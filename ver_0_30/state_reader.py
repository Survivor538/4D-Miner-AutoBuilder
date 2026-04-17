import time

from read_position import get_7coords
from config import READ_RETRY_INTERVAL, READ_RETRY_TIMES
from data_types import PlayerState, ExpectedAction
from utils import (
    grid_of,
    grid_center,
    is_near_center,
    classify_standard_plane,
    is_standard_facing,
)

class StateReader:
    def __init__(self):
        self.last_raw_state = None
        self.last_good_state = None

    def read_raw_state(self):
        raw = get_7coords()
        self.last_raw_state = raw
        return raw

    def validate_raw_state_format(self, raw) -> bool:
        if raw is False:
            return False
        if not isinstance(raw, (list, tuple)):
            return False
        if len(raw) != 7:
            return False

        try:
            [float(v) for v in raw]
        except Exception:
            return False

        return True

    def build_player_state(self, raw) -> PlayerState:
        pos_x, pos_y, pos_z, pos_w, face_x, face_z, face_w = [float(v) for v in raw]

        grid_x = grid_of(pos_x)
        grid_y = round(pos_y)
        grid_z = grid_of(pos_z)
        grid_w = grid_of(pos_w)

        center_x = grid_center(grid_x)
        center_z = grid_center(grid_z)
        center_w = grid_center(grid_w)

        state = PlayerState(
            pos_x=pos_x,
            pos_y=pos_y,
            pos_z=pos_z,
            pos_w=pos_w,
            face_x=face_x,
            face_z=face_z,
            face_w=face_w,
            grid_x=grid_x,
            grid_y=grid_y,
            grid_z=grid_z,
            grid_w=grid_w,
            center_x=center_x,
            center_z=center_z,
            center_w=center_w,
            in_center_x=is_near_center(pos_x, grid_x),
            in_center_z=is_near_center(pos_z, grid_z),
            in_center_w=is_near_center(pos_w, grid_w),
            standard_plane=classify_standard_plane(face_x, face_z, face_w),
        )
        return state

    def is_state_continuous(self, new_state: PlayerState, expected_action=ExpectedAction.NONE) -> bool:
        if self.last_good_state is None:
            return True

        old = self.last_good_state

        dx = abs(new_state.pos_x - old.pos_x)
        dy = abs(new_state.pos_y - old.pos_y)
        dz = abs(new_state.pos_z - old.pos_z)
        dw = abs(new_state.pos_w - old.pos_w)

        # 横向严格
        if dx > 2 or dz > 2 or dw > 2:
            return False

        # 纵向宽松一些，避免建柱后误杀
        if dy > 20:
            return False

        return True

    '''
    #调试使用
    def is_state_continuous(self, new_state: PlayerState, expected_action=ExpectedAction.NONE) -> bool:
        if self.last_good_state is None:
            print("[is_state_continuous] no last_good_state -> True")
            return True

        old = self.last_good_state

        dx = abs(new_state.pos_x - old.pos_x)
        dy = abs(new_state.pos_y - old.pos_y)
        dz = abs(new_state.pos_z - old.pos_z)
        dw = abs(new_state.pos_w - old.pos_w)

        print(
            "[is_state_continuous] "
            f"old=({old.pos_x:.3f},{old.pos_y:.3f},{old.pos_z:.3f},{old.pos_w:.3f}) "
            f"new=({new_state.pos_x:.3f},{new_state.pos_y:.3f},{new_state.pos_z:.3f},{new_state.pos_w:.3f}) "
            f"delta=({dx:.3f},{dy:.3f},{dz:.3f},{dw:.3f})"
        )

        if dx > 5 or dy > 5 or dz > 5 or dw > 5:
            print("[is_state_continuous] -> False")
            return False

        print("[is_state_continuous] -> True")
        return True
    '''

    def read_trusted_state(self, expected_action=ExpectedAction.NONE, retry_times=None):
        if retry_times is None:
            retry_times = READ_RETRY_TIMES

        for _ in range(retry_times):
            raw = self.read_raw_state()

            if not self.validate_raw_state_format(raw):
                time.sleep(READ_RETRY_INTERVAL)
                continue

            state = self.build_player_state(raw)

            if not is_standard_facing(state.face_x, state.face_z, state.face_w):
                # 这里先不直接否掉，因为你后面可能有非 reset 状态读取
                pass

            if not self.is_state_continuous(state, expected_action):
                time.sleep(READ_RETRY_INTERVAL)
                continue

            self.commit_good_state(state)
            return state

        return False

    """
    #调试使用
    def read_trusted_state(self, expected_action=ExpectedAction.NONE, retry_times=None):
        if retry_times is None:
            retry_times = READ_RETRY_TIMES

        for i in range(retry_times):
            raw = self.read_raw_state()
            print(f"[read_trusted_state] try={i}, raw={raw!r}")

            if not self.validate_raw_state_format(raw):
                print(f"[read_trusted_state] try={i} fail: invalid raw format")
                time.sleep(READ_RETRY_INTERVAL)
                continue

            state = self.build_player_state(raw)
            print(
                "[read_trusted_state] try={} state: "
                "pos=({:.3f},{:.3f},{:.3f},{:.3f}) face=({:.3f},{:.3f},{:.3f})".format(
                    i,
                    state.pos_x, state.pos_y, state.pos_z, state.pos_w,
                    state.face_x, state.face_z, state.face_w
                )
            )

            ok = self.is_state_continuous(state, expected_action)
            print(f"[read_trusted_state] try={i} continuous={ok}")

            if not ok:
                print(f"[read_trusted_state] try={i} fail: not continuous")
                time.sleep(READ_RETRY_INTERVAL)
                continue

            self.commit_good_state(state)
            print(f"[read_trusted_state] try={i} success")
            return state

        print("[read_trusted_state] all retries failed")
        return False
    """

    def commit_good_state(self, state: PlayerState):
        self.last_good_state = state

    def reset_history(self):
        self.last_raw_state = None
        self.last_good_state = None
