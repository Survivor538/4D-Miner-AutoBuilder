from data_types import ExpectedAction
import config

class Navigator:
    def __init__(self, controller, state_reader):
        self.c = controller
        self.sr = state_reader

        # 当前视角平面缓存：None / "zx" / "zw"
        self._view_plane = None

        # 连续移动计数
        self._steps_since_normalize = 0
        self._steps_since_force_reset = 0

    # =========================
    # config 读取
    # =========================
    def _cfg(self, name, default):
        return getattr(config, name, default)

    def _renormalize_every(self):
        return int(self._cfg("LONG_MOVE_RENORMALIZE_EVERY", 3))

    def _reset_every(self):
        return int(self._cfg("LONG_MOVE_RESET_EVERY", 3))

    # =========================
    # 基础 normalize
    # =========================    
    '''
    #调试使用
    def normalize_zx(self, force=False):
        print(f"[normalize_zx] enter force={force}, _view_plane={self._view_plane}")
        if force or self._view_plane != "zx":
            print("[normalize_zx] do reset_view_ctrlzx")
            self.c.reset_view_ctrlzx()

        state = self.sr.read_trusted_state(ExpectedAction.RESET_ZX)
        print(f"[normalize_zx] read_trusted_state -> {state!r}")

        if state:
            self._view_plane = "zx"
            self._steps_since_normalize = 0
            self._steps_since_force_reset = 0
            print("[normalize_zx] success")
        else:
            print("[normalize_zx] fail")

        return state
    '''

    def normalize_zx(self, force=False):
        if force or self._view_plane != "zx":
            self.c.reset_view_ctrlzx()
        state = self.sr.read_trusted_state(ExpectedAction.RESET_ZX)
        if state:
            self._view_plane = "zx"
            self._steps_since_normalize = 0
            self._steps_since_force_reset = 0
        return state

    def normalize_zw(self, force=False):
        if force or self._view_plane != "zw":
            self.c.reset_view_ctrlzw()
        state = self.sr.read_trusted_state(ExpectedAction.RESET_ZW)
        if state:
            self._view_plane = "zw"
            self._steps_since_normalize = 0
            self._steps_since_force_reset = 0
        return state

    def ensure_centered(self, preferred_plane="zx", force=False):
        if preferred_plane == "zx":
            return self.normalize_zx(force=force)
        return self.normalize_zw(force=force)

    def clear_navigation_state(self):
        self._view_plane = None
        self._steps_since_normalize = 0
        self._steps_since_force_reset = 0

    # =========================
    # 内部辅助：取动作前状态
    # =========================
    def _get_before_state(self, preferred_plane="zx"):
        """
        获取动作前可信状态。
        如果已有 last_good_state，则直接使用；
        否则先 normalize 到对应平面后读取。
        """
        before = self.sr.last_good_state
        if before:
            return before

        return self.ensure_centered(preferred_plane=preferred_plane, force=True)

    # =========================
    # 内部辅助：按需做周期性重校正
    # =========================
    def _should_force_renormalize(self):
        renorm_every = self._renormalize_every()
        reset_every = self._reset_every()

        if renorm_every > 0 and self._steps_since_normalize >= renorm_every:
            return True

        if reset_every > 0 and self._steps_since_force_reset >= reset_every:
            return True

        return False

    def _prepare_plane_for_step(self, preferred_plane):
        """
        单步移动前准备视角平面：
        - 若当前平面不对：切换
        - 若连续移动过多：周期性强制 refresh
        - 否则不重复 reset
        """
        force = self._should_force_renormalize()

        if preferred_plane == "zx":
            return self.normalize_zx(force=force)
        return self.normalize_zw(force=force)

    # =========================
    # 内部辅助：校验单轴是否按预期变化
    # =========================
    def _validate_axis_step(self, before, after, axis: str, delta: int, step_name: str):
        """
        只要求目标轴变化正确，其余轴格坐标不应变化。
        """
        if not after:
            print(f"[{step_name}] 读取动作后状态失败")
            return False

        axis_map_before = {
            "x": before.grid_x,
            "z": before.grid_z,
            "w": before.grid_w,
        }
        axis_map_after = {
            "x": after.grid_x,
            "z": after.grid_z,
            "w": after.grid_w,
        }

        expected_target = axis_map_before[axis] + delta
        actual_target = axis_map_after[axis]

        if actual_target != expected_target:
            print(
                f"[{step_name}] 目标轴变化错误: axis={axis}, "
                f"before={axis_map_before[axis]}, after={actual_target}, expected={expected_target}"
            )
            return False

        for other_axis in ("x", "z", "w"):
            if other_axis == axis:
                continue
            if axis_map_after[other_axis] != axis_map_before[other_axis]:
                print(
                    f"[{step_name}] 非目标轴发生变化: axis={other_axis}, "
                    f"before={axis_map_before[other_axis]}, after={axis_map_after[other_axis]}"
                )
                return False

        return True

    # =========================
    # 内部统一单步执行
    # =========================
    def _step_with_validation(
        self,
        preferred_plane: str,
        expected_action,
        axis: str,
        delta: int,
        move_func,
        step_name: str,
    ):
        before = self._get_before_state(preferred_plane=preferred_plane)
        if not before:
            print(f"[{step_name}] 无法取得动作前状态")
            return False

        prepared = self._prepare_plane_for_step(preferred_plane)
        if not prepared:
            print(f"[{step_name}] prepare plane 失败")
            return False

        # 动作前状态以最新可信状态为准
        before = self.sr.last_good_state or before

        move_func()

        after = self.sr.read_trusted_state(expected_action)
        ok = self._validate_axis_step(before, after, axis, delta, step_name)

        if ok:
            self._steps_since_normalize += 1
            self._steps_since_force_reset += 1
            return True

        # 失败后清空平面缓存，逼迫下次强制 normalize
        self._view_plane = None
        return False

    # =========================
    # 单步移动：ZX 平面
    # =========================
    def step_plus_x(self):
        """
        这里保持你原有映射语义：
        若你项目里已确认 +x 对应 move_left，就继续这样。
        """
        return self._step_with_validation(
            preferred_plane="zx",
            expected_action=ExpectedAction.MOVE_PLUS_X,
            axis="x",
            delta=1,
            move_func=self.c.move_left,
            step_name="step_plus_x",
        )

    def step_minus_x(self):
        """
        你给的片段里已确认：-x 对应 move_right
        """
        return self._step_with_validation(
            preferred_plane="zx",
            expected_action=ExpectedAction.MOVE_MINUS_X,
            axis="x",
            delta=-1,
            move_func=self.c.move_right,
            step_name="step_minus_x",
        )

    def step_plus_z(self):
        return self._step_with_validation(
            preferred_plane="zx",
            expected_action=ExpectedAction.MOVE_PLUS_Z,
            axis="z",
            delta=1,
            move_func=self.c.move_forward,
            step_name="step_plus_z",
        )

    def step_minus_z(self):
        return self._step_with_validation(
            preferred_plane="zx",
            expected_action=ExpectedAction.MOVE_MINUS_Z,
            axis="z",
            delta=-1,
            move_func=self.c.move_back,
            step_name="step_minus_z",
        )

    # =========================
    # 单步移动：ZW 平面
    # =========================
    def step_plus_w(self):
        """
        这里请保持你项目里已经验证过的映射。
        如果你现有代码定义的是 +w 对应 move_left，就保持不变。
        """
        return self._step_with_validation(
            preferred_plane="zw",
            expected_action=ExpectedAction.MOVE_PLUS_W,
            axis="w",
            delta=1,
            move_func=self.c.move_left,
            step_name="step_plus_w",
        )

    def step_minus_w(self):
        """
        同理，这里按你现有项目已确认的映射。
        """
        return self._step_with_validation(
            preferred_plane="zw",
            expected_action=ExpectedAction.MOVE_MINUS_W,
            axis="w",
            delta=-1,
            move_func=self.c.move_right,
            step_name="step_minus_w",
        )

    # =========================
    # 对外统一单步接口
    # =========================
    def step_axis(self, axis: str, delta: int):
        if axis == "x":
            return self.step_plus_x() if delta > 0 else self.step_minus_x()
        elif axis == "z":
            return self.step_plus_z() if delta > 0 else self.step_minus_z()
        elif axis == "w":
            return self.step_plus_w() if delta > 0 else self.step_minus_w()
        else:
            raise ValueError(f"unknown axis: {axis}")

    # =========================
    # move_to
    # 保持原策略：逐轴逼近
    # 只优化动作切换与 reset 节奏
    # =========================
    def move_to(self, target_x, target_z, target_w):
        before = self.sr.last_good_state
        if not before:
            before = self.ensure_centered(preferred_plane="zx", force=True)

        if not before:
            print("[move_to] 无法读取初始状态")
            return False

        cur_x = before.grid_x
        cur_z = before.grid_z
        cur_w = before.grid_w

        print(
            f"[move_to] from=({cur_x},{cur_z},{cur_w}) "
            f"to=({target_x},{target_z},{target_w})"
        )

        # 不改你的策略，只减少不必要 reset
        while cur_w != target_w:
            ok = self.step_plus_w() if target_w > cur_w else self.step_minus_w()
            if not ok:
                print("[move_to] w 方向移动失败")
                return False
            cur_w += 1 if target_w > cur_w else -1
            
        while cur_x != target_x:
            ok = self.step_plus_x() if target_x > cur_x else self.step_minus_x()
            if not ok:
                print("[move_to] x 方向移动失败")
                return False
            cur_x += 1 if target_x > cur_x else -1

        while cur_z != target_z:
            ok = self.step_plus_z() if target_z > cur_z else self.step_minus_z()
            if not ok:
                print("[move_to] z 方向移动失败")
                return False
            cur_z += 1 if target_z > cur_z else -1



        return True
