"""
自动校准模块（第二版）

约定：
1. reset(ctrlzx) 后，理想朝向 face ~= (0, 1, 0)，即朝 +z
2. TURNBACKSTEP 校准目标：
   reset 后执行 look_right(step)，使朝向尽量接近 (0, -1, 0)
3. METER 校准目标：
   reset 后沿 +z 前进，使 dz 尽量接近 1.0，且 dx/dw 尽量接近 0
4. 所有测试前都应 reset_history()，避免 state_reader 的连续性缓存干扰
"""

import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, List, Tuple

from config import RESET_WAIT

CALIBRATION_FILE = "runtime_calibration.json"

# =========================
# 数据结构
# =========================

@dataclass
class CalibrationResult:
    turnbackstep: Optional[int] = None
    meter: Optional[float] = None
    updated_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# =========================
# 持久化
# =========================

def load_calibration_result(path: str = CALIBRATION_FILE) -> Optional[CalibrationResult]:
    if not os.path.exists(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    return CalibrationResult(
        turnbackstep=data.get("turnbackstep"),
        meter=data.get("meter"),
        updated_at=data.get("updated_at"),
    )

def save_calibration_result(result: CalibrationResult, path: str = CALIBRATION_FILE) -> None:
    payload = result.to_dict()
    payload["updated_at"] = time.time()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# =========================
# 基础辅助
# =========================

def _sleep_after_reset():
    time.sleep(RESET_WAIT)

def _extract_facing(state) -> Optional[Tuple[float, float, float]]:
    if not state:
        return None
    try:
        return float(state.face_x), float(state.face_z), float(state.face_w)
    except (AttributeError, TypeError, ValueError):
        return None

def _extract_position(state) -> Optional[Tuple[float, float, float]]:
    if not state:
        return None
    try:
        return float(state.pos_x), float(state.pos_z), float(state.pos_w)
    except (AttributeError, TypeError, ValueError):
        return None

def _reset_and_read_state(controller, state_reader):
    """
    每次校准前统一做：
    1. reset_history()
    2. reset_view_ctrlzx()
    3. 等待稳定
    4. 再 reset_history()
    5. 读可信状态
    """
    state_reader.reset_history()
    controller.reset_view_ctrlzx()
    _sleep_after_reset()
    state_reader.reset_history()
    return state_reader.read_trusted_state()

def _turnback_error_from_state(state) -> Optional[float]:
    """
    目标朝向：face ~= (0, -1, 0)
    error 越小越好
    """
    facing = _extract_facing(state)
    if not facing:
        return None

    fx, fz, fw = facing
    return abs(fx - 0.0) + abs(fz + 1.0) + abs(fw - 0.0)

def _meter_delta(before_state, after_state) -> Optional[Tuple[float, float, float]]:
    before_pos = _extract_position(before_state)
    after_pos = _extract_position(after_state)
    if not before_pos or not after_pos:
        return None

    bx, bz, bw = before_pos
    ax, az, aw = after_pos
    return ax - bx, az - bz, aw - bw

def _meter_error(before_state, after_state) -> Optional[float]:
    """
    目标：
      dz ~= 1.0
      dx ~= 0.0
      dw ~= 0.0
    """
    delta = _meter_delta(before_state, after_state)
    if not delta:
        return None

    dx, dz, dw = delta
    return abs(dz - 1.0) + abs(dx) + abs(dw)

def _average(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return sum(values) / len(values)

def _max_value(values: List[float]) -> Optional[float]:
    if not values:
        return None
    return max(values)

def _nearly_equal(a: float, b: float, eps: float = 1e-9) -> bool:
    return abs(a - b) <= eps

def _select_best_candidates_by_error(
    scores: List[Tuple[float, float]],
    eps: float = 1e-9,
) -> List[Tuple[float, float]]:
    """
    从 [(candidate, error), ...] 中取出误差并列最优的一组。
    """
    if not scores:
        return []

    min_error = min(err for _, err in scores)
    best_group = [(cand, err) for cand, err in scores if _nearly_equal(err, min_error, eps)]
    return best_group

def _resolve_tie_for_meter(
    tied_scores: List[Tuple[float, float]],
    coarse_best_meter: float,
    verbose: bool = True,
) -> Tuple[float, float]:
    """
    METER 同分处理规则：
    1. 优先选更接近粗搜最佳值的
    2. 若距离也相同，选较小值（保证稳定可复现）
    """
    if len(tied_scores) == 1:
        return tied_scores[0]

    if verbose:
        tied_values = [v for v, _ in tied_scores]
        print(f"[校准 METER] 细搜出现同分候选: {tied_values}")

    tied_scores_sorted = sorted(
        tied_scores,
        key=lambda item: (abs(item[0] - coarse_best_meter), item[0])
    )

    chosen = tied_scores_sorted[0]

    if verbose:
        print(
            f"[校准 METER] 同分处理：优先选择更接近粗搜最佳值 {coarse_best_meter:.4f} 的候选，"
            f"最终选中 {chosen[0]:.4f}"
        )

    return chosen

# =========================
# TURNBACKSTEP：单次测试
# =========================

def evaluate_turnbackstep_once(controller, state_reader, step: int, verbose: bool = True) -> Optional[float]:
    before = _reset_and_read_state(controller, state_reader)
    if not before:
        if verbose:
            print(f"[校准 TURNBACKSTEP] step={step}，reset 后读取初始状态失败")
        return None

    controller.look_right(step)
    time.sleep(0.05)

    state_reader.reset_history()
    after = state_reader.read_trusted_state()
    if not after:
        if verbose:
            print(f"[校准 TURNBACKSTEP] step={step}，旋转后读取状态失败")
        return None

    error = _turnback_error_from_state(after)
    if error is None:
        if verbose:
            print(f"[校准 TURNBACKSTEP] step={step}，无法解析朝向")
        return None

    if verbose:
        before_facing = _extract_facing(before)
        after_facing = _extract_facing(after)
        print(
            f"[校准 TURNBACKSTEP] step={step}, "
            f"before={before_facing}, after={after_facing}, error={error:.6f}"
        )

    return error

# =========================
# TURNBACKSTEP：复验
# =========================

def verify_turnbackstep(
    controller,
    state_reader,
    step: int,
    trials: int = 3,
    verbose: bool = True,
) -> Dict[str, Any]:
    errors: List[float] = []

    if verbose:
        print(f"\n=== 开始复验 TURNBACKSTEP={step} ===")

    for i in range(trials):
        if verbose:
            print(f"[复验 TURNBACKSTEP] 第 {i+1}/{trials} 次")

        before = _reset_and_read_state(controller, state_reader)
        if not before:
            if verbose:
                print("[复验 TURNBACKSTEP] 读取初始状态失败")
            continue

        controller.look_right(step)
        time.sleep(0.05)

        state_reader.reset_history()
        after = state_reader.read_trusted_state()
        if not after:
            if verbose:
                print("[复验 TURNBACKSTEP] 读取动作后状态失败")
            continue

        error = _turnback_error_from_state(after)
        if error is None:
            if verbose:
                print("[复验 TURNBACKSTEP] 无法解析朝向")
            continue

        errors.append(error)

        if verbose:
            print(
                f"[复验 TURNBACKSTEP] after={_extract_facing(after)}, error={error:.6f}"
            )

    result = {
        "step": step,
        "trials": trials,
        "success_count": len(errors),
        "avg_error": _average(errors),
        "max_error": _max_value(errors),
    }

    if verbose:
        print(f"[复验 TURNBACKSTEP] 结果: {result}")

    return result

# =========================
# TURNBACKSTEP：两段式搜索
# =========================

def calibrate_turnbackstep(
    controller,
    state_reader,
    coarse_candidates: Optional[List[int]] = None,
    fine_radius: int = 2,
    verify_trials: int = 3,
    verbose: bool = True,
) -> Optional[int]:
    if coarse_candidates is None:
        coarse_candidates = list(range(8, 19))

    coarse_scores: List[Tuple[int, float]] = []

    if verbose:
        print("\n=== 开始校准 TURNBACKSTEP：粗搜 ===")

    for step in coarse_candidates:
        error = evaluate_turnbackstep_once(controller, state_reader, step, verbose=verbose)
        if error is not None:
            coarse_scores.append((step, error))

    if not coarse_scores:
        print("[校准 TURNBACKSTEP] 粗搜失败：没有可用结果")
        return None

    coarse_scores.sort(key=lambda x: x[1])
    coarse_best_step, coarse_best_error = coarse_scores[0]

    if verbose:
        print(f"[校准 TURNBACKSTEP] 粗搜最佳: step={coarse_best_step}, error={coarse_best_error:.6f}")

    fine_candidates = list(range(max(1, coarse_best_step - fine_radius), coarse_best_step + fine_radius + 1))
    fine_scores: List[Tuple[int, float]] = []

    if verbose:
        print("\n=== 开始校准 TURNBACKSTEP：细搜 ===")

    for step in fine_candidates:
        error = evaluate_turnbackstep_once(controller, state_reader, step, verbose=verbose)
        if error is not None:
            fine_scores.append((step, error))

    if not fine_scores:
        print("[校准 TURNBACKSTEP] 细搜失败，回退使用粗搜结果")
        best_step = coarse_best_step
    else:
        fine_scores.sort(key=lambda x: x[1])
        best_step, best_error = fine_scores[0]
        if verbose:
            print(f"[校准 TURNBACKSTEP] 最终结果: step={best_step}, error={best_error:.6f}")

    verify_turnbackstep(
        controller=controller,
        state_reader=state_reader,
        step=best_step,
        trials=verify_trials,
        verbose=verbose,
    )

    return best_step

# =========================
# METER：单次测试
# =========================

def evaluate_meter_once(controller, state_reader, meter_value: float, verbose: bool = True) -> Optional[float]:
    before = _reset_and_read_state(controller, state_reader)
    if not before:
        if verbose:
            print(f"[校准 METER] meter={meter_value:.4f}，reset 后读取初始状态失败")
        return None

    controller.move_forward(meter_value)
    time.sleep(0.05)

    state_reader.reset_history()
    after = state_reader.read_trusted_state()
    if not after:
        if verbose:
            print(f"[校准 METER] meter={meter_value:.4f}，移动后读取状态失败")
        return None

    error = _meter_error(before, after)
    if error is None:
        if verbose:
            print(f"[校准 METER] meter={meter_value:.4f}，无法解析坐标")
        return None

    if verbose:
        before_pos = _extract_position(before)
        after_pos = _extract_position(after)
        delta = _meter_delta(before, after)
        print(
            f"[校准 METER] meter={meter_value:.4f}, "
            f"before={before_pos}, after={after_pos}, delta={delta}, error={error:.6f}"
        )

    return error

# =========================
# METER：多次平均测试
# =========================

def evaluate_meter_average(
    controller,
    state_reader,
    meter_value: float,
    trials: int = 3,
    verbose: bool = True,
) -> Optional[float]:
    errors: List[float] = []

    for i in range(trials):
        if verbose:
            print(f"[校准 METER] meter={meter_value:.4f}，第 {i+1}/{trials} 次测试")
        error = evaluate_meter_once(controller, state_reader, meter_value, verbose=verbose)
        if error is not None:
            errors.append(error)

    avg_error = _average(errors)
    if avg_error is None:
        if verbose:
            print(f"[校准 METER] meter={meter_value:.4f}，所有测试都失败")
        return None

    if verbose:
        print(f"[校准 METER] meter={meter_value:.4f}，平均误差={avg_error:.6f}")

    return avg_error

# =========================
# METER：复验
# =========================

def verify_meter(
    controller,
    state_reader,
    meter_value: float,
    trials: int = 5,
    verbose: bool = True,
) -> Dict[str, Any]:
    errors: List[float] = []
    deltas: List[Tuple[float, float, float]] = []

    if verbose:
        print(f"\n=== 开始复验 METER={meter_value:.4f} ===")

    for i in range(trials):
        if verbose:
            print(f"[复验 METER] 第 {i+1}/{trials} 次")

        before = _reset_and_read_state(controller, state_reader)
        if not before:
            if verbose:
                print("[复验 METER] 读取初始状态失败")
            continue

        controller.move_forward(meter_value)
        time.sleep(0.05)

        state_reader.reset_history()
        after = state_reader.read_trusted_state()
        if not after:
            if verbose:
                print("[复验 METER] 读取动作后状态失败")
            continue

        error = _meter_error(before, after)
        delta = _meter_delta(before, after)

        if error is None or delta is None:
            if verbose:
                print("[复验 METER] 无法解析位移")
            continue

        errors.append(error)
        deltas.append(delta)

        if verbose:
            dx, dz, dw = delta
            print(
                f"[复验 METER] delta=({dx:.6f}, {dz:.6f}, {dw:.6f}), error={error:.6f}"
            )

    result = {
        "meter": meter_value,
        "trials": trials,
        "success_count": len(errors),
        "avg_error": _average(errors),
        "max_error": _max_value(errors),
        "deltas": deltas,
    }

    if verbose:
        print(f"[复验 METER] 结果: {result}")

    return result

# =========================
# METER：两段式搜索
# =========================

def calibrate_meter(
    controller,
    state_reader,
    coarse_candidates: Optional[List[float]] = None,
    fine_step: float = 0.01,
    fine_radius_steps: int = 2,
    trials: int = 3,
    verify_trials: int = 5,
    verbose: bool = True,
) -> Optional[float]:
    if coarse_candidates is None:
        coarse_candidates = [0.18, 0.20, 0.22, 0.24, 0.25, 0.26, 0.28, 0.30]

    coarse_scores: List[Tuple[float, float]] = []

    if verbose:
        print("\n=== 开始校准 METER：粗搜 ===")

    for meter_value in coarse_candidates:
        avg_error = evaluate_meter_average(
            controller,
            state_reader,
            meter_value,
            trials=trials,
            verbose=verbose,
        )
        if avg_error is not None:
            coarse_scores.append((meter_value, avg_error))

    if not coarse_scores:
        print("[校准 METER] 粗搜失败：没有可用结果")
        return None

    coarse_scores.sort(key=lambda x: x[1])
    coarse_best_meter, coarse_best_error = coarse_scores[0]

    if verbose:
        print(f"[校准 METER] 粗搜最佳: meter={coarse_best_meter:.4f}, error={coarse_best_error:.6f}")

    fine_candidates = []
    for offset in range(-fine_radius_steps, fine_radius_steps + 1):
        value = coarse_best_meter + offset * fine_step
        if value > 0:
            fine_candidates.append(round(value, 4))

    fine_candidates = sorted(set(fine_candidates))
    fine_scores: List[Tuple[float, float]] = []

    if verbose:
        print("\n=== 开始校准 METER：细搜 ===")

    for meter_value in fine_candidates:
        avg_error = evaluate_meter_average(
            controller,
            state_reader,
            meter_value,
            trials=trials,
            verbose=verbose,
        )
        if avg_error is not None:
            fine_scores.append((meter_value, avg_error))

    if not fine_scores:
        print("[校准 METER] 细搜失败，回退使用粗搜结果")
        best_meter = coarse_best_meter
    else:
        best_group = _select_best_candidates_by_error(fine_scores)

        if len(best_group) == 1:
            best_meter, best_error = best_group[0]
            if verbose:
                print(f"[校准 METER] 最终结果: meter={best_meter:.4f}, error={best_error:.6f}")
        else:
            best_meter, best_error = _resolve_tie_for_meter(
                tied_scores=best_group,
                coarse_best_meter=coarse_best_meter,
                verbose=verbose,
            )
            if verbose:
                print(f"[校准 METER] 最终结果（同分裁决后）: meter={best_meter:.4f}, error={best_error:.6f}")

    verify_meter(
        controller=controller,
        state_reader=state_reader,
        meter_value=best_meter,
        trials=verify_trials,
        verbose=verbose,
    )

    return best_meter

# =========================
# 总入口
# =========================

def run_full_calibration(
    controller,
    state_reader,
    verbose: bool = True,
) -> CalibrationResult:
    result = CalibrationResult()

    best_turnbackstep = calibrate_turnbackstep(
        controller=controller,
        state_reader=state_reader,
        verbose=verbose,
    )
    result.turnbackstep = best_turnbackstep

    best_meter = calibrate_meter(
        controller=controller,
        state_reader=state_reader,
        verbose=verbose,
    )
    result.meter = best_meter

    result.updated_at = time.time()
    return result
