from __future__ import annotations

import time
import traceback

from build_entry import relative_to_absolute_structure

from structure import generate_structure
from planner import Planner
from controller import Controller
from state_reader import StateReader
from navigator import Navigator
from builder_actions import BuilderActions
from progress import (
    ProgressManager,
    calc_structure_hash,
    calc_relative_structure_hash,
    extract_resume_player_pos,
)
from data_types import ExpectedAction
from row_executor import execute_rows
from stop_control import StopController
from runtime_params import build_runtime_params
from calibration import (
    load_calibration_result,
    run_full_calibration,
    save_calibration_result,
)
import config

class ResumeOriginState:
    """
    用于从 progress.json 中恢复“原点玩家状态”的轻量对象。
    必须提供 build_entry.py 所要求的属性访问形式：
        player_state.grid_x / grid_z / grid_w
    """

    def __init__(self, grid_x, grid_z, grid_w, y=None):
        self.grid_x = int(grid_x)
        self.grid_z = int(grid_z)
        self.grid_w = int(grid_w)
        self.y = int(y) if y is not None else None

    def __repr__(self):
        return (
            f"ResumeOriginState(grid_x={self.grid_x}, "
            f"grid_z={self.grid_z}, grid_w={self.grid_w}, y={self.y})"
        )

def build_context(runtime_params=None):
    structure = generate_structure()
    planner = Planner(structure)
    controller = Controller(runtime_params=runtime_params)
    state_reader = StateReader()
    navigator = Navigator(controller, state_reader)
    builder_actions = BuilderActions(controller, navigator, state_reader)
    progress_manager = ProgressManager()

    return {
        "structure": structure,
        "planner": planner,
        "controller": controller,
        "state_reader": state_reader,
        "navigator": navigator,
        "builder_actions": builder_actions,
        "progress_manager": progress_manager,
    }

def handle_runtime_error(exc: Exception):
    print("\n[main_row] 程序运行异常：")
    print(exc)
    print("\n[main_row] traceback:")
    traceback.print_exc()

def validate_relative_structure(relative_structure):
    if relative_structure is None:
        raise ValueError("generate_structure() 返回了 None")

    if not relative_structure:
        raise ValueError("generate_structure() 返回空结构，无法执行建造")

    checked = set()

    for i, point in enumerate(relative_structure, start=1):
        if not isinstance(point, tuple):
            raise TypeError(f"第 {i} 个点不是 tuple: {point!r}")

        if len(point) != 4:
            raise ValueError(f"第 {i} 个点不是 4 元组 (dx, y, dz, dw): {point!r}")

        dx, y, dz, dw = point

        for name, value in [("dx", dx), ("y", y), ("dz", dz), ("dw", dw)]:
            if not isinstance(value, int):
                raise TypeError(f"第 {i} 个点中的 {name} 不是 int: {point!r}")

        checked.add((dx, y, dz, dw))

    return checked

def print_relative_structure_summary(relative_structure):
    if not relative_structure:
        print("[main_row] relative_structure 为空")
        return

    xs = [x for x, _, _, _ in relative_structure]
    ys = [y for _, y, _, _ in relative_structure]
    zs = [z for _, _, z, _ in relative_structure]
    ws = [w for _, _, _, w in relative_structure]

    print("\n[main_row] ==== relative structure summary ====")
    print({
        "point_count": len(relative_structure),
        "min_dx": min(xs),
        "max_dx": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_dz": min(zs),
        "max_dz": max(zs),
        "min_dw": min(ws),
        "max_dw": max(ws),
    })

def print_rows_summary(rows):
    print("\n[main_row] ==== rows summary ====")
    print(f"row_count = {len(rows)}")
    for i, row in enumerate(rows, start=1):
        print(f"  row {i}: column_count = {len(row)}")

def ask_yes_no(prompt: str, default=False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    s = input(prompt + suffix).strip().lower()
    if not s:
        return default
    return s in ("y", "yes", "1", "true")

def ensure_calibration_file():
    """
    如果不存在校准结果，则询问是否现在执行自动校准。
    校准成功后保存 runtime_calibration.json。
    """
    calibration = load_calibration_result()
    if calibration is not None:
        print("[main_row] 已检测到校准文件，将直接使用。")
        return

    print("[main_row] 未检测到校准文件 runtime_calibration.json。")

    if not ask_yes_no("是否现在进行自动校准？", default=True):
        print("[main_row] 你选择跳过自动校准，将继续使用 config.py 默认参数。")
        return

    print("\n[main_row] ==== auto calibration ====")
    print("请确保：")
    print("1. 角色站在平整、空旷、无遮挡的位置")
    print("2. 前方有足够长的直线空间")
    print("3. 视角和人物状态稳定")
    input(
        "按回车后将在 "
        + str(config.START_DELAY_SECONDS)
        + " 秒后开始自动校准，请立即切回游戏窗口"
    )
    time.sleep(config.START_DELAY_SECONDS)

    calibration_controller = Controller()
    calibration_state_reader = StateReader()

    result = run_full_calibration(
        controller=calibration_controller,
        state_reader=calibration_state_reader,
        verbose=True,
    )

    print("[main_row] 自动校准完成：", result)

    if result.turnbackstep is None and result.meter is None:
        print("[main_row] 自动校准未得到有效结果，不保存校准文件，继续使用默认参数。")
        return

    save_calibration_result(result)
    print("[main_row] 校准结果已保存到 runtime_calibration.json")

def get_current_player_state_for_origin(state_reader):
    """
    读取当前玩家状态作为“新任务原点”。
    兼容 read_trusted_state() 失败时返回 False。
    """
    player_state = state_reader.read_trusted_state(
        expected_action=ExpectedAction.NONE,
        retry_times=None,
    )

    if not player_state:
        raise RuntimeError(
            f"无法读取当前玩家状态，read_trusted_state 返回了: {player_state!r}"
        )

    for attr in ("grid_x", "grid_z", "grid_w"):
        if not hasattr(player_state, attr):
            raise RuntimeError(
                f"当前玩家状态缺少属性 {attr}，实际值为: {player_state!r}"
            )

    return player_state

def build_origin_state_from_resume_pos(resume_player_pos: dict):
    """
    把 progress.json 中保存的 resume_player_pos 还原成
    relative_to_absolute_structure(...) 可接受的对象。
    """
    if not resume_player_pos:
        raise ValueError("resume_player_pos 为空，无法恢复")

    if (
        "grid_x" not in resume_player_pos
        or "grid_z" not in resume_player_pos
        or "grid_w" not in resume_player_pos
    ):
        raise ValueError(f"resume_player_pos 缺少必要字段: {resume_player_pos!r}")

    return ResumeOriginState(
        grid_x=resume_player_pos["grid_x"],
        grid_z=resume_player_pos["grid_z"],
        grid_w=resume_player_pos["grid_w"],
        y=resume_player_pos.get("y"),
    )

def run():
    ensure_calibration_file()

    runtime_params = build_runtime_params()

    print("[main_row] 参数来源 =", runtime_params.source)
    print("[main_row] TURNBACKSTEP =", runtime_params.turnbackstep)
    print("[main_row] METER =", runtime_params.meter)
    print("当前运行模式：ROW")
    print("当前约定：structure 的 x/z/w 相对原点玩家，y 不相对")
    print("运行过程中可按 F8 请求停止，程序会在安全点停下并保存断点")
    print("请将指南针放于副手，死亡镐放于物品栏第二格，物块放于物品栏第8格")

    ctx = build_context(runtime_params=runtime_params)

    controller = ctx["controller"]
    state_reader = ctx["state_reader"]
    builder_actions = ctx["builder_actions"]
    progress_manager = ctx["progress_manager"]

    stop_controller = StopController(hotkey="f8")
    stop_controller.start()

    try:
        print("\n[main_row] ==== generate relative structure ====")
        relative_structure = generate_structure()
        relative_structure = validate_relative_structure(relative_structure)
        print_relative_structure_summary(relative_structure)

        relative_structure_hash = calc_relative_structure_hash(relative_structure)
        print(f"[main_row] relative_structure_hash = {relative_structure_hash}")

        print("\n[main_row] ==== load progress ====")
        resume_info = None
        origin_player_state_for_build = None
        origin_resume_player_pos_for_save = None

        saved = progress_manager.load()

        if saved and saved.get("relative_structure_hash") == relative_structure_hash:
            print("[main_row] 检测到相同相对结构的可恢复断点：")
            print(saved)

            if ask_yes_no("是否从断点恢复？", default=True):
                resume_info = saved

                saved_resume_player_pos = saved.get("resume_player_pos")
                if not saved_resume_player_pos:
                    raise RuntimeError(
                        "断点文件缺少 resume_player_pos，无法在非原点位置安全恢复。"
                    )

                origin_player_state_for_build = build_origin_state_from_resume_pos(
                    saved_resume_player_pos
                )
                origin_resume_player_pos_for_save = saved_resume_player_pos

                print("[main_row] 本次恢复将使用 progress.json 中记录的原点：")
                print(origin_resume_player_pos_for_save)
            else:
                progress_manager.clear()
                print("[main_row] 已清除旧断点，从头开始")

        elif saved:
            print("[main_row] 检测到旧断点，但 relative_structure_hash 不匹配，不自动恢复")
            if ask_yes_no("是否清除旧断点？", default=True):
                progress_manager.clear()

        print("\n[main_row] ==== game operation confirmation ====")
        if resume_info is None:
            print("本次是从头开始构建。")
            print("请站在你希望作为相对结构原点的位置。")
        else:
            print("本次是从断点恢复。")
            print("不要求你必须站回原点，但建议站在安全且未被结构卡住的位置。")

        input(
            "即将开始游戏操作（选方块/读状态/导航/建造），按回车后在"
            + str(config.START_DELAY_SECONDS)
            + "秒内切回游戏窗口"
        )
        time.sleep(config.START_DELAY_SECONDS)

        print("\n[main_row] ==== select block ====")
        controller.select_block()
        time.sleep(0.5)

        if origin_player_state_for_build is None:
            print("\n[main_row] ==== read current player state ====")
            if hasattr(state_reader, "reset_history"):
                state_reader.reset_history()

            current_player_state = get_current_player_state_for_origin(state_reader)
            origin_player_state_for_build = current_player_state
            origin_resume_player_pos_for_save = extract_resume_player_pos(current_player_state)

            print("[main_row] 本次新建任务使用当前站位作为原点：")
            print(origin_resume_player_pos_for_save)

        print("\n[main_row] ==== relative -> absolute structure ====")
        absolute_structure = relative_to_absolute_structure(
            relative_structure,
            origin_player_state_for_build,
        )
        structure_hash = calc_structure_hash(absolute_structure)
        print(f"[main_row] structure_hash = {structure_hash}")

        print("\n[main_row] ==== build rows ====")
        planner = Planner(absolute_structure, fill_mode="row_local")
        rows = planner.build_rows()

        if not rows:
            raise RuntimeError("planner.build_rows() 返回空 rows，无法执行建造")

        print_rows_summary(rows)

        first_non_empty_row = next((row for row in rows if row), None)
        if first_non_empty_row is None:
            raise RuntimeError("rows 中没有任何可执行 column task")

        column_task_cls = type(first_non_empty_row[0])

        if resume_info is None:
            print("\n[main_row] ==== save initial progress anchor ====")
            progress_manager.save_row_resume(
                structure_hash=structure_hash,
                relative_structure_hash=relative_structure_hash,
                row_idx=0,
                next_col_idx=0,
                phase="real_columns",
                prev_actual_top=0,
                prev_column_y_values=None,
                aux_actual_top=0,
                resume_player_pos=origin_resume_player_pos_for_save,
            )
        else:
            print("\n[main_row] ==== resume mode: skip initial progress anchor ====")

        print("\n[main_row] ==== execute rows ====")
        if hasattr(state_reader, "reset_history"):
            print("[main_row] 执行前重置 state_reader 历史")
            state_reader.reset_history()

        ok, result = execute_rows(
            builder=builder_actions,
            rows=rows,
            column_task_cls=column_task_cls,
            aux_z_offset=1,
            sleep_between_rows=0.5,
            sleep_between_columns=0.3,
            progress_manager=progress_manager,
            structure_hash=structure_hash,
            relative_structure_hash=relative_structure_hash,
            stop_controller=stop_controller,
            resume_info=resume_info,
            resume_player_pos=origin_resume_player_pos_for_save,
        )

        print("\n[main_row] ==== final result ====")
        print("ok =", ok)

        if not ok:
            if result.get("stopped"):
                print("[main_row] 已按请求停止，断点已保存")
            else:
                print("[main_row] 构建失败")
            print("result =", result)
            return

        print("[main_row] 构建完成")
        print("[main_row] all_results =", result.get("all_results"))

        progress_manager.clear()

    except Exception as exc:
        handle_runtime_error(exc)

    finally:
        stop_controller.shutdown()

if __name__ == "__main__":
    run()
