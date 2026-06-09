import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import VEHICLE_HOST, VEHICLE_PORT

log = logging.getLogger(__name__)

router = APIRouter(prefix="/lights", tags=["Lights"])


class LightResponse(BaseModel):
    status: str
    vehicle: str


@router.post("/on", response_model=LightResponse, summary="Turn lights on")
def lights_on():
    return LightResponse(status="ok", vehicle=f"{VEHICLE_HOST}:{VEHICLE_PORT}")


@router.post("/off", response_model=LightResponse, summary="Turn lights off")
def lights_off():
    log.info(f"LIGHTS OFF  (vehicle={VEHICLE_HOST}:{VEHICLE_PORT})")
    return LightResponse(status="ok", vehicle=f"{VEHICLE_HOST}:{VEHICLE_PORT}")
