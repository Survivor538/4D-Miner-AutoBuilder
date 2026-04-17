from collections import defaultdict
from typing import Optional

from data_types import ColumnTask
from structure import get_column_map

Point4D = tuple[int, int, int, int]   # (x, y, z, w)
ColumnKey = tuple[int, int, int]      # (x, z, w)
RowKey = tuple[int, int]              # (w, x)

class Planner:
    """
    将 4D 结构点集 structure -> rows

    当前项目约定：
    - 输入 structure: set[(x, y, z, w)]
    - 输出 rows: list[list[ColumnTask]]
    - 每个 row 固定一个 (x, w)
    - 行内 z 必须连续补齐
    - 中间缺失柱补为空柱任务：
        ColumnTask(..., y_values=[], is_auxiliary=False)
    - planner 不生成辅助柱
    - 行尾辅助柱由 row_executor.execute_row(...) 自动补

    默认顺序：
    - 行顺序：w -> x
    - 行内顺序：z 递增
    """

    def __init__(self, structure: set[Point4D], fill_mode: str = "row_local"):
        """
        fill_mode:
        - row_local: 每行只补该行真实柱的 min_z..max_z
        - global_w: 同一个 w 层内所有行统一补该层 min_z..max_z
        - global_all: 全结构所有行统一补全局 min_z..max_z

        推荐先用 row_local。
        """
        self.structure = set(structure)
        self.fill_mode = fill_mode

        valid_modes = {"row_local", "global_w", "global_all"}
        if fill_mode not in valid_modes:
            raise ValueError(f"fill_mode must be one of {valid_modes}, got {fill_mode}")

    # =========================
    # 基础信息
    # =========================

    def is_empty(self) -> bool:
        return len(self.structure) == 0

    def get_bounds(self) -> Optional[dict]:
        if not self.structure:
            return None

        xs = [x for x, y, z, w in self.structure]
        ys = [y for x, y, z, w in self.structure]
        zs = [z for x, y, z, w in self.structure]
        ws = [w for x, y, z, w in self.structure]

        return {
            "min_x": min(xs),
            "max_x": max(xs),
            "min_y": min(ys),
            "max_y": max(ys),
            "min_z": min(zs),
            "max_z": max(zs),
            "min_w": min(ws),
            "max_w": max(ws),
        }

    # =========================
    # structure -> column_map
    # =========================

    def build_column_map(self) -> dict[ColumnKey, list[int]]:
        """
        复用 structure.py 中的 get_column_map:
            (x, z, w) -> sorted unique y_values
        """
        return get_column_map(self.structure)

    # =========================
    # column_map -> real_rows
    # =========================

    def _collect_real_rows(
        self,
        column_map: dict[ColumnKey, list[int]]
    ) -> dict[RowKey, dict[int, list[int]]]:
        """
        整理为：
            (w, x) -> { z: y_values }

        只包含真实柱。
        """
        real_rows: dict[RowKey, dict[int, list[int]]] = defaultdict(dict)

        for (x, z, w), y_values in column_map.items():
            real_rows[(w, x)][z] = y_values

        return real_rows

    def _compute_global_z_range(self) -> Optional[tuple[int, int]]:
        if not self.structure:
            return None
        zs = [z for x, y, z, w in self.structure]
        return min(zs), max(zs)

    def _compute_w_level_z_ranges(
        self,
        column_map: dict[ColumnKey, list[int]]
    ) -> dict[int, tuple[int, int]]:
        """
        计算：
            w -> (min_z, max_z)
        """
        z_map: dict[int, list[int]] = defaultdict(list)

        for (x, z, w) in column_map.keys():
            z_map[w].append(z)

        result: dict[int, tuple[int, int]] = {}
        for w, zs in z_map.items():
            result[w] = (min(zs), max(zs))

        return result

    def _get_fill_z_range_for_row(
        self,
        row_key: RowKey,
        real_z_to_y: dict[int, list[int]],
        w_level_z_ranges: dict[int, tuple[int, int]],
        global_z_range: Optional[tuple[int, int]],
    ) -> tuple[int, int]:
        """
        决定某一行应该补齐到哪个 z 区间。
        """
        w, x = row_key

        if not real_z_to_y:
            raise ValueError(f"row {row_key} has no real columns")

        if self.fill_mode == "row_local":
            zs = sorted(real_z_to_y.keys())
            return zs[0], zs[-1]

        if self.fill_mode == "global_w":
            return w_level_z_ranges[w]

        if self.fill_mode == "global_all":
            if global_z_range is None:
                raise ValueError("global_z_range is None while structure is not empty")
            return global_z_range

        raise ValueError(f"unsupported fill_mode: {self.fill_mode}")

    # =========================
    # 构造 ColumnTask
    # =========================

    def _make_task(
        self,
        x: int,
        z: int,
        w: int,
        y_values: list[int],
        is_auxiliary: bool = False,
    ) -> ColumnTask:
        return ColumnTask(
            x=x,
            z=z,
            w=w,
            y_values=list(y_values),
            is_auxiliary=is_auxiliary,
        )

    # =========================
    # 生成 rows
    # =========================

    def build_rows(self) -> list[list[ColumnTask]]:
        """
        输出：
            rows: list[list[ColumnTask]]

        规则：
        - 每个 row 固定一个 (x, w)
        - 行内 z 连续
        - 真实柱保留真实 y_values
        - 缺失柱补成空柱 y_values=[]
        - 不生成辅助柱
        - 行顺序：w -> x
        """
        if not self.structure:
            return []

        column_map = self.build_column_map()
        real_rows = self._collect_real_rows(column_map)
        w_level_z_ranges = self._compute_w_level_z_ranges(column_map)
        global_z_range = self._compute_global_z_range()

        rows: list[list[ColumnTask]] = []

        for row_key in sorted(real_rows.keys()):   # (w, x)
            w, x = row_key
            real_z_to_y = real_rows[row_key]

            z_start, z_end = self._get_fill_z_range_for_row(
                row_key=row_key,
                real_z_to_y=real_z_to_y,
                w_level_z_ranges=w_level_z_ranges,
                global_z_range=global_z_range,
            )

            row_tasks: list[ColumnTask] = []
            for z in range(z_start, z_end + 1):
                y_values = real_z_to_y.get(z, [])
                row_tasks.append(
                    self._make_task(
                        x=x,
                        z=z,
                        w=w,
                        y_values=y_values,
                        is_auxiliary=False,
                    )
                )

            rows.append(row_tasks)

        return rows

    # =========================
    # 调试 / 统计
    # =========================

    def summarize_rows(self, rows: Optional[list[list[ColumnTask]]] = None) -> dict:
        if rows is None:
            rows = self.build_rows()

        row_count = len(rows)
        total_tasks = sum(len(row) for row in rows)
        real_tasks = 0
        empty_tasks = 0

        for row in rows:
            for task in row:
                if task.y_values:
                    real_tasks += 1
                else:
                    empty_tasks += 1

        return {
            "row_count": row_count,
            "total_tasks": total_tasks,
            "real_tasks": real_tasks,
            "empty_tasks": empty_tasks,
            "fill_mode": self.fill_mode,
        }

    def debug_print_rows(self, rows: Optional[list[list[ColumnTask]]] = None) -> None:
        if rows is None:
            rows = self.build_rows()

        print("\n[planner] rows:")
        for i, row in enumerate(rows):
            if not row:
                print(f"  row[{i}] <empty>")
                continue

            fixed_x = row[0].x
            fixed_w = row[0].w
            z_start = row[0].z
            z_end = row[-1].z

            print(f"  row[{i}] x={fixed_x}, w={fixed_w}, z={z_start}..{z_end}")

            for task in row:
                kind = "REAL" if task.y_values else "EMPTY"
                print(
                    f"    z={task.z:>3}  type={kind:<5}  "
                    f"y_values={task.y_values}  aux={task.is_auxiliary}"
                )

# =========================
# 便捷函数
# =========================

def structure_to_rows(
    structure: set[Point4D],
    fill_mode: str = "row_local",
) -> list[list[ColumnTask]]:
    planner = Planner(structure=structure, fill_mode=fill_mode)
    return planner.build_rows()
