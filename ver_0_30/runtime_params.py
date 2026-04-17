from dataclasses import dataclass

import config
from calibration import load_calibration_result

@dataclass
class RuntimeParams:
    turnbackstep: int
    meter: float
    source: str = "config"

def build_runtime_params() -> RuntimeParams:
    params = RuntimeParams(
        turnbackstep=config.TURNBACKSTEP,
        meter=config.METER,
        source="config",
    )

    calibration = load_calibration_result()
    if calibration is not None:
        used_calibration = False

        if calibration.turnbackstep is not None:
            params.turnbackstep = calibration.turnbackstep
            used_calibration = True

        if calibration.meter is not None:
            params.meter = calibration.meter
            used_calibration = True

        if used_calibration:
            params.source = "runtime_calibration.json"

    return params
