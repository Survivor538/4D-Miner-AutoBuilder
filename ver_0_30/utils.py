from config import GRID_CENTER_TOLERANCE, FACE_TOLERANCE

def grid_of(value: float) -> int:
    return int(value // 1)

def grid_center(grid: int) -> float:
    return grid + 0.5

def near(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol

def is_near_center(pos_value: float, grid: int, tol: float = GRID_CENTER_TOLERANCE) -> bool:
    return near(pos_value, grid_center(grid), tol)

def normalize_column_y_values(y_values: list[int]) -> list[int]:
    return sorted(set(y_values))

def classify_standard_plane(face_x: float, face_z: float, face_w: float) -> str:
    """
    当前先做简化判断：
    - 如果 facing 在 x/z 上是标准轴，认为是 zx
    - 如果 facing 在 z/w 上是标准轴，认为是 zw
    - 更精细规则后续再补
    """
    axes = [face_x, face_z, face_w]

    # 严格标准值之一
    standard_values = {-1.0, 0.0, 1.0}
    rounded = [round(v, 3) for v in axes]

    if not all(v in standard_values for v in rounded):
        return "unknown"

    # 简化策略：先默认归到 zx
    # 后续可根据 reset 预期动作进一步判断
    return "zx"

def is_standard_facing(face_x: float, face_z: float, face_w: float) -> bool:
    vals = [round(face_x, 3), round(face_z, 3), round(face_w, 3)]
    return all(v in (-1.0, 0.0, 1.0) for v in vals)
