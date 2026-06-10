import logging
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from kuksa_client.grpc import Datapoint, VSSClient
from pydantic import BaseModel

from app.config import CLIENT_ID, DEMO_STEP_DELAY_SECONDS, VEHICLE_HOST, VEHICLE_PORT

log = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["Demo"])


class DemoStep(BaseModel):
    name: str
    signal: str
    value: str
    status: str
    detail: Optional[str] = None


class DemoSequenceResponse(BaseModel):
    status: str
    vehicle: str
    steps: List[DemoStep]


_SEQUENCE = [
    ("takeover", "Vehicle.RequestTakeOver", str([1, CLIENT_ID])),
    ("start_engine", "Vehicle.Powertrain.StartStop.StartControl", str([1, CLIENT_ID])),
    ("accelerate", "Vehicle.Chassis.Accelerator.PedalPositionControl", str([50, CLIENT_ID])),
    ("stop_accelerating", "Vehicle.Chassis.Accelerator.PedalPositionControl", str([0, CLIENT_ID])),
    ("low_beam_on", "Vehicle.Body.Lights.ExteriorLightControl", str([1, 5, CLIENT_ID])),
    ("low_beam_off", "Vehicle.Body.Lights.ExteriorLightControl", str([0, 5, CLIENT_ID])),
    ("stop_engine", "Vehicle.Powertrain.StartStop.StartControl", str([0, CLIENT_ID])),
    ("release_control", "Vehicle.RequestTakeOver", str([0, CLIENT_ID])),
]


@router.post("/sequence", response_model=DemoSequenceResponse, summary="Run KUKSA car demo sequence")
def run_demo_sequence():
    steps: List[DemoStep] = []
    vehicle = f"{VEHICLE_HOST}:{VEHICLE_PORT}"

    try:
        with VSSClient(VEHICLE_HOST, VEHICLE_PORT) as client:
            for name, signal, value in _SEQUENCE:
                try:
                    client.set_current_values({signal: Datapoint(value)})
                    steps.append(DemoStep(name=name, signal=signal, value=value, status="ok"))
                    log.info("DEMO STEP %s -> %s %s", name, signal, value)
                    time.sleep(DEMO_STEP_DELAY_SECONDS)
                except Exception as exc:
                    steps.append(
                        DemoStep(
                            name=name,
                            signal=signal,
                            value=value,
                            status="skipped",
                            detail=str(exc),
                        )
                    )
                    log.warning("DEMO STEP SKIPPED %s -> %s: %s", name, signal, exc)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    ok_count = sum(1 for step in steps if step.status == "ok")
    if ok_count == 0:
        raise HTTPException(status_code=502, detail="No demo sequence steps succeeded.")

    status = "ok" if ok_count == len(steps) else "partial"
    return DemoSequenceResponse(status=status, vehicle=vehicle, steps=steps)
