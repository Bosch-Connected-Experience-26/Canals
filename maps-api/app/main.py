from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.geocode import router as geocode_router
from app.route import router as route_router
from app.ev import router as ev_router

app = FastAPI(
    title="Canals Route Proxy",
    description="Proxy for OSM routing and EV charging data along a route.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(geocode_router)
app.include_router(route_router)
app.include_router(ev_router)
