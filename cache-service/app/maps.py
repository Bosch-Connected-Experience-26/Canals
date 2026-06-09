from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.config import MAPS_API_URL


async def fetch_waypoints(start: str, end: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{MAPS_API_URL}/route/cities", params={"start": start, "end": end}
        )
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
        "source_id":   str(station["id"]),
        "poi_type":    "ev_charging",
        "name":        station["name"],
        "location":    {"type": "Point", "coordinates": [station["lng"], station["lat"]]},
        "town":        station.get("town"),
        "country":     station.get("country"),
        "connections": station.get("connections", 0),
        "journey_id":  journey_id,
        "cached_at":   datetime.now(timezone.utc).isoformat(),
    }
