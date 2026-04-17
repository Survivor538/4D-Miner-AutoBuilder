from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Literal, Optional

StandardPlane = Literal["zx", "zw", "unknown"]

class ExpectedAction(Enum):
    NONE = auto()

    RESET_ZX = auto()
    RESET_ZW = auto()

    MOVE_PLUS_X = auto()
    MOVE_MINUS_X = auto()
    MOVE_PLUS_Z = auto()
    MOVE_MINUS_Z = auto()
    MOVE_PLUS_W = auto()
    MOVE_MINUS_W = auto()

    MOVE_TO_TARGET = auto()

    JUMP_PUT = auto()
    BREAK_BLOCK = auto()

    RECOVER = auto()

@dataclass(frozen=True)
class GridPos:
    x: int
    y: int
    z: int
    w: int

@dataclass
class PlayerState:
    pos_x: float
    pos_y: float
    pos_z: float
    pos_w: float

    face_x: float
    face_z: float
    face_w: float

    grid_x: int
    grid_y: int
    grid_z: int
    grid_w: int

    center_x: float
    center_z: float
    center_w: float

    in_center_x: bool
    in_center_z: bool
    in_center_w: bool

    standard_plane: StandardPlane

@dataclass
class ColumnTask:
    x: int
    z: int
    w: int
    y_values: list[int]
    is_auxiliary: bool = False

@dataclass
class ScanLineTask:
    scanline_id: str
    fixed_x: int
    fixed_w: int
    z_start: int
    z_end: int
    safe_base: GridPos
    columns: list[ColumnTask] = field(default_factory=list)

@dataclass
class ProgressState:
    current_scanline_id: str = ""
    current_z_index: int = 0
    current_w: int = 0
    current_x: int = 0
    last_safe_base: Optional[GridPos] = None
    finished_scanlines: list[str] = field(default_factory=list)
