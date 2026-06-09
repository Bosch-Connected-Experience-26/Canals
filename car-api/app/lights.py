import logging

from fastapi import APIRouter, HTTPException
from kuksa_client.grpc import Datapoint, VSSClient
from pydantic import BaseModel

from app.config import VEHICLE_HOST, VEHICLE_PORT, CLIENT_ID

log = logging.getLogger(__name__)

router = APIRouter(prefix="/lights", tags=["Lights"])

_TAKEOVER = "Vehicle.RequestTakeOver"
_SIGNAL   = "Vehicle.Body.Lights.ExteriorLightControl"


class LightResponse(BaseModel):
    status: str
    vehicle: str


def _send(values: dict) -> None:
    with VSSClient(VEHICLE_HOST, VEHICLE_PORT) as client:
        client.set_current_values({_TAKEOVER: Datapoint(str([1, CLIENT_ID]))})
        client.set_current_values(values)


@router.post("/on", response_model=LightResponse, summary="Turn lights on")
def lights_on():
    try:
        _send({_SIGNAL: Datapoint(str([1, 5, CLIENT_ID]))})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return LightResponse(status="ok", vehicle=f"{VEHICLE_HOST}:{VEHICLE_PORT}")


@router.post("/off", response_model=LightResponse, summary="Turn lights off")
def lights_off():
    log.info(f"LIGHTS OFF  (vehicle={VEHICLE_HOST}:{VEHICLE_PORT})")
    try:
        _send({_SIGNAL: Datapoint(str([0, 0, CLIENT_ID]))})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return LightResponse(status="ok", vehicle=f"{VEHICLE_HOST}:{VEHICLE_PORT}")
