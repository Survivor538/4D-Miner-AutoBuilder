import os
import json
import hashlib
from datetime import datetime

DEFAULT_PROGRESS_FILE = "progress.json"

def _stable_hash_from_iterable_points(points) -> str:
    normalized = sorted([list(item) for item in points])
    raw = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def calc_structure_hash(structure) -> str:
    """
    绝对结构哈希。
    structure 预期为 [(x, y, z, w), ...] 或 set[(x, y, z, w), ...]
    """
    return _stable_hash_from_iterable_points(structure)

def calc_relative_structure_hash(relative_structure) -> str:
    """
    相对结构哈希。
    relative_structure 预期为 [(dx, y, dz, dw), ...] 或 set[(dx, y, dz, dw), ...]
    """
    return _stable_hash_from_iterable_points(relative_structure)

def extract_resume_player_pos(player_state):
    """
    从 player_state 中提取可用于恢复原点的信息。
    """
    if not player_state:
        raise ValueError(f"player_state 不能为空，实际为: {player_state!r}")

    def get_attr_or_key(obj, name, default=None):
        if isinstance(obj, dict):
            return obj.get(name, default)
        return getattr(obj, name, default)

    grid_x = get_attr_or_key(player_state, "grid_x")
    grid_z = get_attr_or_key(player_state, "grid_z")
    grid_w = get_attr_or_key(player_state, "grid_w")

    y = get_attr_or_key(player_state, "y", None)
    if y is None:
        y = get_attr_or_key(player_state, "grid_y", None)

    if grid_x is None or grid_z is None or grid_w is None:
        raise ValueError(
            f"player_state 缺少恢复所需字段，至少需要 grid_x/grid_z/grid_w: {player_state!r}"
        )

    return {
        "grid_x": int(grid_x),
        "grid_z": int(grid_z),
        "grid_w": int(grid_w),
        "y": int(y) if y is not None else None,
    }

class ProgressManager:
    def __init__(self, path=DEFAULT_PROGRESS_FILE):
        self.path = path

    def save_row_resume(
        self,
        structure_hash: str,
        relative_structure_hash: str,
        row_idx: int,
        next_col_idx: int,
        phase: str,
        prev_actual_top: int,
        prev_column_y_values,
        aux_actual_top: int = 0,
        resume_player_pos=None,
    ):
        data = {
            "version": 3,
            "mode": "row",
            "structure_hash": structure_hash,
            "relative_structure_hash": relative_structure_hash,
            "row_idx": int(row_idx),
            "next_col_idx": int(next_col_idx),
            "phase": phase,
            "prev_actual_top": int(prev_actual_top),
            "prev_column_y_values": (
                list(prev_column_y_values)
                if prev_column_y_values is not None
                else None
            ),
            "aux_actual_top": int(aux_actual_top),
            "resume_player_pos": resume_player_pos,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self):
        if not os.path.exists(self.path):
            return None

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(data, dict):
            return None

        if data.get("mode") != "row":
            return None

        return data

    def clear(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def can_resume_by_relative_hash(self, relative_structure_hash: str) -> bool:
        data = self.load()
        return bool(data and data.get("relative_structure_hash") == relative_structure_hash)

    def can_resume_by_absolute_hash(self, structure_hash: str) -> bool:
        data = self.load()
        return bool(data and data.get("structure_hash") == structure_hash)
