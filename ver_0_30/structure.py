def generate_structure() -> set[tuple[int, int, int, int]]:
    """
    返回目标结构:
        set[(x, y, z, w)]

    这里先给一个最简单示例，后续你替换成真实结构。
    """
    s = set()

    R = 5
    center = R

    for x in range(2*R+1):
        for y in range(2*R+1):
            for z in range(2*R+1):
                for w in range(2*R+1):

                    dx = x - center
                    dy = y - center
                    dz = z - center
                    dw = w - center

                    d2 = dx*dx + dy*dy + dz*dz + dw*dw

                    if R*R - 2 <= d2 <= R*R + 2:
                        s.add((x, y, z, w))

    return s

def get_bounds(structure: set[tuple[int, int, int, int]]) -> dict:
    xs = [p[0] for p in structure]
    ys = [p[1] for p in structure]
    zs = [p[2] for p in structure]
    ws = [p[3] for p in structure]

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

def has_block(structure: set[tuple[int, int, int, int]], x: int, y: int, z: int, w: int) -> bool:
    return (x, y, z, w) in structure

def column_y_values(structure: set[tuple[int, int, int, int]], x: int, z: int, w: int) -> list[int]:
    ys = [p[1] for p in structure if p[0] == x and p[2] == z and p[3] == w]
    return sorted(set(ys))

def get_column_map(structure: set[tuple[int, int, int, int]]) -> dict[tuple[int, int, int], list[int]]:
    result = {}
    for x, y, z, w in structure:
        key = (x, z, w)
        result.setdefault(key, []).append(y)

    for key in result:
        result[key] = sorted(set(result[key]))

    return result
