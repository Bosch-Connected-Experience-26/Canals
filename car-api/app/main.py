import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import VEHICLE_HOST, VEHICLE_PORT
from app.lights import router as lights_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [CAR-API]  %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(
    title="Car API",
    description=f"Vehicle control API. Connected to **{VEHICLE_HOST}:{VEHICLE_PORT}**.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lights_router)
