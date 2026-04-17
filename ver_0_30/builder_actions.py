import time
import config

class BuilderActions:
    def __init__(self, controller, navigator, state_reader):
        self.c = controller
        self.nav = navigator
        self.sr = state_reader

        # 当前工具缓存：None / "block" / "pickaxe"
        self._equipped_tool = None

        # 当前动作模式：None / "jump_put" / "break_prev" / "break_down"
        self._action_mode = None

        # 当前模式下连续执行次数
        self._mode_action_count = 0

    # =========================
    # config 读取
    # =========================
    def _cfg(self, name, default):
        return getattr(config, name, default)

    def _turnbackstep(self):
        """
        优先使用 controller 中的运行时参数。
        若不存在，则退回 config 或安全默认值。
        """
        if hasattr(self.c, "turnbackstep"):
            return self.c.turnbackstep
        return self._cfg("TURNBACKSTEP", 13)

    def _jump_put_look_down_steps(self):
        return int(self._turnbackstep() * self._cfg("LOOK_DOWN_JUMP_PUT_RATIO", 0.6))

    def _break_prev_look_down_steps(self):
        # BREAK_RATIO: 挖上一柱的低头比例
        return int(self._turnbackstep() * self._cfg("BREAK_RATIO", 0.4))

    def _break_down_look_down_steps(self):
        # BREAK_WHOLE_COLUMN_LOOK_DOWN_RATIO: 挖当前脚下柱的低头比例
        return int(
            self._turnbackstep() * self._cfg("BREAK_WHOLE_COLUMN_LOOK_DOWN_RATIO", 0.6)
        )

    def _build_reset_every(self):
        return int(self._cfg("BUILD_RESET_EVERY_N_BLOCKS", 3))

    def _break_reset_every(self):
        return int(self._cfg("BREAK_RESET_EVERY_N_BLOCKS", 3))

    def _action_interval(self):
        return float(self._cfg("COLUMN_ACTION_INTERVAL", 0.03))

    def _finish_wait(self):
        return float(self._cfg("COLUMN_FINISH_WAIT", 0.05))

    def _jump_put_wait(self):
        return float(self._cfg("JUMP_PUT_WAIT", 0.08))

    def _jump_put_post_click_wait(self):
        return float(self._cfg("JUMP_PUT_POST_CLICK_WAIT", 0.08))

    def _final_place_settle_wait(self):
        return float(self._cfg("COLUMN_FINAL_PLACE_SETTLE_WAIT", 0.20))

    # =========================
    # 工具切换缓存
    # =========================
    def equip_block(self, force=False):
        if force or self._equipped_tool != "block":
            self.c.select_block()
            self._equipped_tool = "block"

    def equip_pickaxe(self, force=False):
        if force or self._equipped_tool != "pickaxe":
            self.c.select_pickaxe()
            self._equipped_tool = "pickaxe"

    # =========================
    # 动作模式管理
    # =========================
    def _clear_mode_only(self):
        self._action_mode = None
        self._mode_action_count = 0

    def cleanup_action_state(self, reset_view=True):
        """
        收尾用：
        - 退出任何连续动作模式
        - 视情况恢复标准视角
        """
        if reset_view:
            self.c.reset_view_ctrlzx()
            time.sleep(self._finish_wait())

        self._clear_mode_only()

    def _enter_mode(self, mode: str):
        """
        进入指定动作模式。
        这里统一负责：
        - 切工具
        - reset 到标准视角
        - 调整到该模式需要的视角
        """
        self._clear_mode_only()
        self._action_mode = mode

        if mode == "jump_put":
            self.equip_block()
            self.c.reset_view_ctrlzx()
            self.c.look_down(self._jump_put_look_down_steps())
            time.sleep(self._finish_wait())

        elif mode == "break_prev":
            self.equip_pickaxe()
            self.c.reset_view_ctrlzx()
            self.c.look_right(self._turnbackstep())
            self.c.look_down(self._break_prev_look_down_steps())
            time.sleep(self._finish_wait())

        elif mode == "break_down":
            self.equip_pickaxe()
            self.c.reset_view_ctrlzx()
            self.c.look_down(self._break_down_look_down_steps())
            time.sleep(self._finish_wait())

        else:
            raise ValueError(f"unknown action mode: {mode}")

    def _switch_mode(self, new_mode: str):
        """
        切换模式时不额外先 reset 一次，
        因为 _enter_mode() 自己就会 reset。
        """
        if self._action_mode == new_mode:
            return
        self._enter_mode(new_mode)

    def _refresh_current_mode(self):
        if self._action_mode is None:
            return
        current_mode = self._action_mode
        self._enter_mode(current_mode)

    # =========================
    # 兼容旧接口
    # =========================
    def break_one_block(self):
        self.equip_pickaxe()
        self.c.left_click()

    # =========================
    # 连续 jump_put
    # =========================
    def begin_continuous_jump_put(self):
        self._switch_mode("jump_put")

    def continuous_jump_put_once(self):
        """
        只执行一次放置动作，不在这里自动 refresh。
        refresh 由 build_column 外层控制，避免最后一层刚放完就被 reset 打断。
        """
        if self._action_mode != "jump_put":
            self.begin_continuous_jump_put()

        self.equip_block()
        self.c.jump()
        time.sleep(self._jump_put_wait())
        self.c.right_click()
        time.sleep(self._jump_put_post_click_wait())

        self._mode_action_count += 1

    def end_continuous_jump_put(self, reset_view=True):
        self.cleanup_action_state(reset_view=reset_view)

    def jump_put(self):
        """
        保留旧接口：单次 jump_put
        """
        self.begin_continuous_jump_put()
        self.continuous_jump_put_once()
        time.sleep(self._final_place_settle_wait())
        self.end_continuous_jump_put(reset_view=True)

    def place_block_at_current_layer(self):
        """
        兼容旧接口：
        若外部只调用这个函数，会自动进入连续模式并执行一次。
        """
        self.begin_continuous_jump_put()
        self.continuous_jump_put_once()

    # =========================
    # 清理上一柱当前层
    # =========================
    def break_prev_once(self):
        """
        清理上一柱在当前高度的一块。
        BREAK_RATIO = 0.4 用在这里。
        """
        self._switch_mode("break_prev")
        self.equip_pickaxe()
        self.c.left_click()
        time.sleep(self._action_interval())
        self._mode_action_count += 1

    # =========================
    # 连续向下挖（用于 break_whole_column）
    # =========================
    def begin_continuous_break_down(self):
        self._switch_mode("break_down")

    def continuous_break_down_once(self):
        if self._action_mode != "break_down":
            self.begin_continuous_break_down()

        self.equip_pickaxe()
        self.c.left_click()
        time.sleep(max(0.08, self._action_interval()))

        self._mode_action_count += 1

    def end_continuous_break_down(self, reset_view=True):
        self.cleanup_action_state(reset_view=reset_view)

    def break_block_at_current_layer(self):
        """
        兼容旧接口。
        更接近“向下挖当前柱”的语义。
        """
        self.begin_continuous_break_down()
        self.continuous_break_down_once()

    # =========================
    # 内部辅助
    # =========================
    def _get_column_top(self, y_values):
        if not y_values:
            return 0
        return max(y_values) + 1

    # =========================
    # build_column
    # 不改策略，只优化动作
    # =========================
    def build_column(self, task_column, prev_column_y_values=None, prev_actual_top=0):
        """
        保留原策略：

        - task_column.y_values：当前柱最终应保留的层
        - prev_column_y_values：上一柱最终应保留的层
        - prev_actual_top：上一柱实际被建到的高度（开区间）

        当前柱实际建造高度：
            actual_top = max(cur_final_top, prev_actual_top)

        每层逻辑：
        - 若上一柱在这一层“实际存在但最终不该存在”，则回头挖
        - 若 y < actual_top，则当前柱继续向上搭
        """
        print(
            f"[build_column] x={task_column.x}, z={task_column.z}, w={task_column.w}, "
            f"ys={task_column.y_values}, aux={task_column.is_auxiliary}, "
            f"prev_y={prev_column_y_values}, prev_actual_top={prev_actual_top}"
        )

        # 开始前确保姿态干净
        self.cleanup_action_state(reset_view=True)
        self.sr.reset_history()

        ok = self.nav.move_to(task_column.x, task_column.z, task_column.w)
        if not ok:
            print("[build_column] 导航失败")
            self.cleanup_action_state(reset_view=True)
            return False, 0

        prev_final_set = set(prev_column_y_values or [])
        cur_final_top = self._get_column_top(task_column.y_values)

        # 不改你的建造策略
        actual_top = max(cur_final_top, prev_actual_top)

        if actual_top <= 0:
            print("[build_column] actual_top=0，无需处理")
            self.cleanup_action_state(reset_view=True)
            return True, 0

        print(
            f"[build_column] cur_final_top={cur_final_top}, "
            f"prev_actual_top={prev_actual_top}, actual_top={actual_top}"
        )

        for y in range(actual_top):
            prev_actually_exists = y < prev_actual_top
            prev_should_remain = (
                y in prev_final_set if prev_column_y_values is not None else False
            )

            need_break_prev = (
                prev_column_y_values is not None
                and prev_actually_exists
                and not prev_should_remain
            )

            print(
                f"  -> y={y}, "
                f"prev_actually_exists={prev_actually_exists}, "
                f"prev_should_remain={prev_should_remain}, "
                f"need_break_prev={need_break_prev}"
            )

            if need_break_prev:
                self.break_prev_once()

            # 不改策略：每层继续搭当前柱
            self.begin_continuous_jump_put()
            self.continuous_jump_put_once()

            # 只有“后面还有下一层”时才 refresh
            # 避免最后一层刚放完就被 reset，导致少搭一层
            if y < actual_top - 1:
                if self._mode_action_count >= self._build_reset_every():
                    self._refresh_current_mode()

        # 最后一层放完后，额外等一下，让落块稳定
        time.sleep(self._final_place_settle_wait())

        # 列结束后统一恢复标准姿态
        self.cleanup_action_state(reset_view=True)
        return True, actual_top

    # =========================
    # break_whole_column
    # 只优化动作，不改用途
    # =========================
    def break_whole_column(self, actual_top):
        """
        清理当前所在位置整根“实际已建成”的柱子
        """
        print(f"[break_whole_column] actual_top={actual_top}")

        if actual_top <= 0:
            actual_top = 1

        self.cleanup_action_state(reset_view=True)
        self.begin_continuous_break_down()

        for i in range(actual_top):
            print(f"  -> break layer {i}")
            self.continuous_break_down_once()

            # 只有后面还有下一层时才 refresh
            if i < actual_top - 1:
                if self._mode_action_count >= self._break_reset_every():
                    self._refresh_current_mode()

        self.cleanup_action_state(reset_view=True)
        self.equip_block()
        return True
