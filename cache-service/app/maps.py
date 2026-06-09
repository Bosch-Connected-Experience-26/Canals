import random
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import HTTPException

from app.config import MAPS_API_URL

_CHARGER_TYPES = (Path(__file__).parent.parent / "input" / "charger_types.txt").read_text().splitlines()
_SLOTS_WEIGHTS = [11 - i for i in range(11)]  # [11,10,9,...,1] — triangular, biased toward 0


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


def _generate_opening_times() -> dict:
    # ~35% of German EV stations are open 24/7 (motorways, petrol stations)
    if random.random() < 0.35:
        return {"type": "24/7"}

    open_hour  = random.choice([6, 7, 8, 9])
    close_hour = random.choice([18, 19, 20, 21, 22])
    sat_open   = random.choice([8, 9, 10])
    sat_close  = random.choice([16, 17, 18])
    sun_open   = random.choice([10, 11])
    sun_close  = random.choice([14, 15, 16])

    return {
        "type":      "scheduled",
        "weekdays":  {"open": f"{open_hour:02d}:00",  "close": f"{close_hour:02d}:00"},
        "saturday":  {"open": f"{sat_open:02d}:00",   "close": f"{sat_close:02d}:00"},
        "sunday":    {"open": f"{sun_open:02d}:00",   "close": f"{sun_close:02d}:00"}
                     if random.random() < 0.5 else "closed",
    }


def build_cloud_poi_doc(base_doc: dict) -> dict:
    return {
        **base_doc,
        "accessible_toilets": random.choice(["yes", "no"]),
        "restaurants_close":  random.choice(["yes", "no"]),
        "opening_times":      _generate_opening_times(),
    }


def build_poi_doc(station: dict, journey_id: str) -> dict:
    return {
        "source_id":   str(station["id"]),
        "poi_type":    "ev_charging",
        "name":        station["name"],
        "location":    {"type": "Point", "coordinates": [station["lng"], station["lat"]]},
        "town":        station.get("town"),
        "country":     station.get("country"),
        "connections": station.get("connections", 0),
        "journey_id":      journey_id,
        "cached_at":       datetime.now(timezone.utc).isoformat(),
        "charger_type":    random.choice(_CHARGER_TYPES),
        "slots_available": random.choices(range(11), weights=_SLOTS_WEIGHTS)[0],
    }
