from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database as db
from app.journey import router as journey_router
from app.offline import router as offline_router

app = FastAPI(
    title="Route Cache Service",
    description="Fetches POIs along a route and stores them in local MongoDB for offline use.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    db.connect()


app.include_router(journey_router)
app.include_router(offline_router)
