#未实装，不要使用


import time

from structure import generate_structure
from planner import Planner
from controller import Controller
from state_reader import StateReader
from navigator import Navigator
from builder_actions import BuilderActions
from progress import ProgressManager
from data_types import ProgressState
import config

def build_context():
    structure = generate_structure()
    planner = Planner(structure)
    controller = Controller()
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

def execute_scanline(scanline, navigator, builder_actions, progress_manager):
    print(f"\n=== 执行扫描线 {scanline.scanline_id} ===")
    print(f"safe_base = {scanline.safe_base}")

    state = navigator.go_to_safe_base(scanline.safe_base)
    if not state:
        raise RuntimeError(f"无法到达扫描线安全基准点: {scanline.scanline_id}")

    prev_column = None

    for idx, column in enumerate(scanline.columns):
        print(f"[scanline] idx={idx}, column=({column.x}, {column.z}, {column.w}), aux={column.is_auxiliary}")

        progress_manager.save(
            ProgressState(
                current_scanline_id=scanline.scanline_id,
                current_z_index=idx,
                current_w=scanline.fixed_w,
                current_x=scanline.fixed_x,
                last_safe_base=scanline.safe_base,
                finished_scanlines=[],
            )
        )

        if column.is_auxiliary:
            # 第一版先简单处理：
            # 如果是辅助柱，先不建，直接调用挖辅助柱接口占位
            builder_actions.break_whole_column()
        else:
            prev_y_values = prev_column.y_values if prev_column else None
            builder_actions.build_column(column, prev_y_values)

        prev_column = column

    print(f"=== 扫描线 {scanline.scanline_id} 完成 ===")

def execute_all_scanlines(scanlines, navigator, builder_actions, progress_manager):
    for scanline in scanlines:
        execute_scanline(scanline, navigator, builder_actions, progress_manager)

def handle_runtime_error(exc, progress_manager):
    print("\n程序运行异常：")
    print(exc)
    print("建议保留 progress.json 以便后续恢复。")

def run():
    print("请确认 TURNBACKSTEP 数值已调好")
    print("请站在目标结构最小坐标处")
    print("ver0.30 第一版骨架将开始运行")
    input("按回车后，5秒后开始，请切换到游戏窗口...")

    time.sleep(config.START_DELAY_SECONDS)

    ctx = build_context()

    planner = ctx["planner"]
    navigator = ctx["navigator"]
    builder_actions = ctx["builder_actions"]
    progress_manager = ctx["progress_manager"]
    controller = ctx["controller"]

    scanlines = planner.build_scanlines()

    print(f"共生成 {len(scanlines)} 条扫描线")

    controller.select_block()

    try:
        # 先同步一次状态
        init_state = navigator.normalize_zx()
        print("初始状态：", init_state)

        execute_all_scanlines(scanlines, navigator, builder_actions, progress_manager)

        print("完成")
    except Exception as exc:
        handle_runtime_error(exc, progress_manager)


if __name__ == "__main__":
    run()


