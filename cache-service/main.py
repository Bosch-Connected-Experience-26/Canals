import os
import uuid
from dotenv import load_dotenv

load_dotenv()
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient, GEOSPHERE
from pymongo.collection import Collection

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

MAPS_API_URL = os.getenv("MAPS_API_URL", "http://maps-api:8000")
MONGODB_URI  = os.getenv("MONGODB_URI", "mongodb://root:root@mongodb:27017/?authSource=admin")
DB_NAME      = os.getenv("MONGODB_DATABASE", "route_cache")
COLLECTION   = os.getenv("MONGODB_COLLECTION", "pois")

mongo: MongoClient = None
pois: Collection   = None


@app.on_event("startup")
def startup():
    global mongo, pois
    mongo = MongoClient(MONGODB_URI)
    pois  = mongo[DB_NAME][COLLECTION]
    pois.create_index([("location", GEOSPHERE)])
    pois.create_index([("journey_id", 1)])
    pois.create_index([("source_id", 1), ("poi_type", 1)], unique=True, sparse=True)


# ── Models ────────────────────────────────────────────────────────────────────

class JourneyRequest(BaseModel):
    start: str
    end: str
    journey_id: Optional[str] = None
    radius_km: int = 10


class JourneyStatus(BaseModel):
    journey_id: str
    start: str
    end: str
    poi_count: int
    status: str
    created_at: str


class PoiSummary(BaseModel):
    source_id: str
    poi_type: str
    name: str
    lat: float
    lng: float
    town: Optional[str]
    country: Optional[str]
    connections: int


# ── Helpers ───────────────────────────────────────────────────────────────────

async def fetch_waypoints(start: str, end: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{MAPS_API_URL}/route/cities", params={"start": start, "end": end})
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Maps API route error: {resp.text}")
    return resp.json()["waypoints"]


async def fetch_ev_stations(lat: float, lng: float, radius_km: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{MAPS_API_URL}/ev-stations",
            params={"lat": lat, "lng": lng, "radius_km": radius_km, "max_results": 50},
        )
    if resp.status_code != 200:
        return []
    return resp.json()


def build_poi_doc(station: dict, journey_id: str) -> dict:
    return {
        "source_id":  str(station["id"]),
        "poi_type":   "ev_charging",
        "name":       station["name"],
        "location":   {"type": "Point", "coordinates": [station["lng"], station["lat"]]},
        "town":       station.get("town"),
        "country":    station.get("country"),
        "connections": station.get("connections", 0),
        "journey_id": journey_id,
        "cached_at":  datetime.now(timezone.utc).isoformat(),
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post(
    "/journey",
    response_model=JourneyStatus,
    summary="Cache all POIs along a route",
    tags=["Journey"],
)
async def create_journey_cache(req: JourneyRequest):
    """
    Geocodes start + end, fetches route waypoints, queries EV stations per waypoint,
    and stores all POIs in local MongoDB tagged with a journey_id.
    """
    journey_id = req.journey_id or str(uuid.uuid4())[:8]

    waypoints = await fetch_waypoints(req.start, req.end)

    seen: set[str] = set()
    stored = 0

    for wp in waypoints:
        stations = await fetch_ev_stations(wp["lat"], wp["lng"], req.radius_km)
        for s in stations:
            key = str(s["id"])
            if key in seen:
                continue
            seen.add(key)
            doc = build_poi_doc(s, journey_id)
            pois.update_one(
                {"source_id": doc["source_id"], "poi_type": "ev_charging"},
                {"$set": doc},
                upsert=True,
            )
            stored += 1

    return JourneyStatus(
        journey_id=journey_id,
        start=req.start,
        end=req.end,
        poi_count=stored,
        status="complete",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get(
    "/journey/{journey_id}",
    response_model=JourneyStatus,
    summary="Get journey cache status",
    tags=["Journey"],
)
def get_journey(journey_id: str):
    """Returns POI count and metadata for a cached journey."""
    count = pois.count_documents({"journey_id": journey_id})
    if count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
    return JourneyStatus(
        journey_id=journey_id,
        start="",
        end="",
        poi_count=count,
        status="complete",
        created_at="",
    )


@app.get(
    "/journey/{journey_id}/pois",
    response_model=list[PoiSummary],
    summary="List cached POIs for a journey",
    tags=["Journey"],
)
def list_pois(journey_id: str, poi_type: Optional[str] = None):
    """Returns all cached POIs for a journey, optionally filtered by poi_type."""
    query: dict = {"journey_id": journey_id}
    if poi_type:
        query["poi_type"] = poi_type

    results = []
    for doc in pois.find(query, {"_id": 0}):
        coords = doc["location"]["coordinates"]
        results.append(PoiSummary(
            source_id=doc["source_id"],
            poi_type=doc["poi_type"],
            name=doc["name"],
            lat=coords[1],
            lng=coords[0],
            town=doc.get("town"),
            country=doc.get("country"),
            connections=doc.get("connections", 0),
        ))
    return results


@app.delete(
    "/journey/{journey_id}",
    summary="Delete cached POIs for a journey",
    tags=["Journey"],
)
def delete_journey(journey_id: str):
    """Removes all cached POIs for the given journey_id."""
    result = pois.delete_many({"journey_id": journey_id})
    return {"journey_id": journey_id, "deleted": result.deleted_count}


@app.get(
    "/nearby",
    response_model=list[PoiSummary],
    summary="Find cached POIs near a position",
    tags=["Offline"],
)
def nearby(lat: float, lng: float, radius_m: float = 10000, poi_type: Optional[str] = None):
    """
    Geospatial query on local cache — works fully offline.
    Returns POIs within radius_m metres of the given coordinate.
    """
    query: dict = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius_m,
            }
        }
    }
    if poi_type:
        query["poi_type"] = poi_type

    results = []
    for doc in pois.find(query, {"_id": 0}):
        coords = doc["location"]["coordinates"]
        results.append(PoiSummary(
            source_id=doc["source_id"],
            poi_type=doc["poi_type"],
            name=doc["name"],
            lat=coords[1],
            lng=coords[0],
            town=doc.get("town"),
            country=doc.get("country"),
            connections=doc.get("connections", 0),
        ))
    return results
