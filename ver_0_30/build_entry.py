from __future__ import annotations

from typing import Iterable

from data_types import ColumnTask
from planner import Planner
from row_executor import execute_rows

Point4D = tuple[int, int, int, int]

def get_player_origin_xzw(player_state) -> tuple[int, int, int]:
    """
    从 player_state 中提取当前人物所在格坐标 (x, z, w)。

    要求 player_state 至少具有：
        - grid_x
        - grid_z
        - grid_w
    """
    try:
        return player_state.grid_x, player_state.grid_z, player_state.grid_w
    except AttributeError as exc:
        raise AttributeError(
            "player_state 必须具有 grid_x / grid_z / grid_w 属性"
        ) from exc

def relative_to_absolute_structure(
    relative_structure: Iterable[Point4D],
    player_state,
) -> set[Point4D]:
    """
    将“相对当前人物位置”的 structure 转换为“绝对世界坐标”的 structure。

    当前约定：
    - x / z / w 相对当前人物位置
    - y 不相对，保持原值

    即：
        (dx, y, dz, dw)
    转成：
        (player.grid_x + dx, y, player.grid_z + dz, player.grid_w + dw)
    """
    origin_x, origin_z, origin_w = get_player_origin_xzw(player_state)

    abs_structure = {
        (origin_x + dx, y, origin_z + dz, origin_w + dw)
        for (dx, y, dz, dw) in relative_structure
    }
    return abs_structure

def summarize_absolute_structure(structure: set[Point4D]) -> dict:
    """
    对绝对 structure 做一个简单摘要，便于调试输出。
    """
    if not structure:
        return {
            "point_count": 0,
            "min_x": None,
            "max_x": None,
            "min_y": None,
            "max_y": None,
            "min_z": None,
            "max_z": None,
            "min_w": None,
            "max_w": None,
        }

    xs = [x for x, _, _, _ in structure]
    ys = [y for _, y, _, _ in structure]
    zs = [z for _, _, z, _ in structure]
    ws = [w for _, _, _, w in structure]

    return {
        "point_count": len(structure),
        "min_x": min(xs),
        "max_x": max(xs),
        "min_y": min(ys),
        "max_y": max(ys),
        "min_z": min(zs),
        "max_z": max(zs),
        "min_w": min(ws),
        "max_w": max(ws),
    }

def plan_rows_from_relative_structure(
    relative_structure: Iterable[Point4D],
    player_state,
    *,
    fill_mode: str = "row_local",
):
    """
    仅负责规划，不执行建造。

    流程：
        relative_structure
        -> absolute_structure
        -> Planner.build_rows()

    返回：
        rows, planner, absolute_structure
    """
    absolute_structure = relative_to_absolute_structure(relative_structure, player_state)
    planner = Planner(absolute_structure, fill_mode=fill_mode)
    rows = planner.build_rows()
    return rows, planner, absolute_structure

def run_build(
    *,
    builder,
    player_state,
    relative_structure: Iterable[Point4D],
    fill_mode: str = "row_local",
    column_task_cls=ColumnTask,
    aux_z_offset: int = 1,
    sleep_between_rows: float = 0.5,
    sleep_between_columns: float = 0.3,
    debug_print_structure_summary: bool = True,
    debug_print_rows: bool = True,
):
    """
    执行完整建造流程。

    参数：
    - builder:
        你的 BuilderActions 实例，要求至少实现：
            build_column(task, prev_column_y_values=None, prev_actual_top=0)
            break_whole_column(actual_top)

    - player_state:
        当前人物状态，要求至少有：
            grid_x, grid_z, grid_w

    - relative_structure:
        相对当前人物位置的结构：
            set/list/iterable[(dx, y, dz, dw)]

    - fill_mode:
        传给 Planner 的补空策略，默认 "row_local"

    返回：
        (ok, result)

    其中 result 示例：
    {
        "origin": (grid_x, grid_z, grid_w),
        "absolute_structure": ...,
        "structure_summary": ...,
        "rows": ...,
        "planner_summary": ...,
        "execute_results": ...,
    }
    """
    origin = get_player_origin_xzw(player_state)

    rows, planner, absolute_structure = plan_rows_from_relative_structure(
        relative_structure=relative_structure,
        player_state=player_state,
        fill_mode=fill_mode,
    )

    structure_summary = summarize_absolute_structure(absolute_structure)
    planner_summary = planner.summarize_rows(rows)

    if debug_print_structure_summary:
        print("\n[build_entry] ==== player origin ====")
        print(f"[build_entry] origin(x,z,w) = {origin}")

        print("\n[build_entry] ==== absolute structure summary ====")
        print(structure_summary)

        print("\n[build_entry] ==== planner summary ====")
        print(planner_summary)

    if debug_print_rows:
        print("\n[build_entry] ==== planner rows ====")
        planner.debug_print_rows(rows)

    ok, execute_results = execute_rows(
        builder=builder,
        rows=rows,
        column_task_cls=column_task_cls,
        aux_z_offset=aux_z_offset,
        sleep_between_rows=sleep_between_rows,
        sleep_between_columns=sleep_between_columns,
    )

    result = {
        "origin": origin,
        "absolute_structure": absolute_structure,
        "structure_summary": structure_summary,
        "rows": rows,
        "planner_summary": planner_summary,
        "execute_results": execute_results,
    }
    return ok, result

def run_build_with_state_reader(
    *,
    builder,
    state_reader,
    relative_structure: Iterable[Point4D],
    fill_mode: str = "row_local",
    column_task_cls=ColumnTask,
    aux_z_offset: int = 1,
    sleep_between_rows: float = 0.5,
    sleep_between_columns: float = 0.3,
    debug_print_structure_summary: bool = True,
    debug_print_rows: bool = True,
    read_state_func_name: str = "read_trusted_state",
    read_state_args: tuple = (),
    read_state_kwargs: dict | None = None,
):
    """
    通过 state_reader 读取人物状态后，再执行建造。

    这样写是为了尽量少耦合你的具体 state_reader 接口。
    你只需要告诉我：
        - 要调用 state_reader 的哪个函数
        - 参数是什么

    默认会尝试调用：
        state_reader.read_trusted_state(*read_state_args, **read_state_kwargs)

    返回：
        (ok, result)

    当读取状态失败时，返回：
        (False, {"error": ...})
    """
    if read_state_kwargs is None:
        read_state_kwargs = {}

    if not hasattr(state_reader, read_state_func_name):
        return False, {
            "error": f"state_reader 不存在函数: {read_state_func_name}"
        }

    read_state_func = getattr(state_reader, read_state_func_name)
    player_state = read_state_func(*read_state_args, **read_state_kwargs)

    if not player_state:
        return False, {
            "error": "读取人物状态失败",
            "player_state": player_state,
        }

    return run_build(
        builder=builder,
        player_state=player_state,
        relative_structure=relative_structure,
        fill_mode=fill_mode,
        column_task_cls=column_task_cls,
        aux_z_offset=aux_z_offset,
        sleep_between_rows=sleep_between_rows,
        sleep_between_columns=sleep_between_columns,
        debug_print_structure_summary=debug_print_structure_summary,
        debug_print_rows=debug_print_rows,
    )
