import httpx
from fastapi import APIRouter, HTTPException

from app.config import OCM_URL, OCM_API_KEY
from app.models import EvStation
from app.route import fetch_route

router = APIRouter(tags=["EV"])


async def fetch_ev_stations(
    lat: float, lng: float, radius_km: int = 10, max_results: int = 20
) -> list[EvStation]:
    if not OCM_API_KEY:
        return _demo_ev_stations(lat, lng, max_results)

    params: dict = {
        "output":       "json",
        "latitude":     lat,
        "longitude":    lng,
        "distance":     radius_km,
        "distanceunit": "KM",
        "maxresults":   max_results,
        "compact":      "true",
        "verbose":      "false",
    }
    params["key"] = OCM_API_KEY

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OCM_URL, params=params)

    if resp.status_code != 200:
        if resp.status_code in {401, 403}:
            return _demo_ev_stations(lat, lng, max_results)
        raise HTTPException(status_code=502, detail=f"OpenChargeMap error {resp.status_code}: {resp.text}")

    stations = []
    for poi in resp.json():
        addr = poi.get("AddressInfo", {})
        country_info = addr.get("Country") or {}
        stations.append(EvStation(
            id=poi.get("ID", 0),
            name=addr.get("Title", "Unknown"),
            lat=addr.get("Latitude", 0.0),
            lng=addr.get("Longitude", 0.0),
            connections=len(poi.get("Connections") or []),
            town=addr.get("Town"),
            country=country_info.get("ISOCode"),
        ))
    return stations


def _demo_ev_stations(lat: float, lng: float, max_results: int) -> list[EvStation]:
    """Deterministic fallback so demos work without a third-party OpenChargeMap key."""
    seeds = [
        ("Canals Route HPC", 0.018, 0.014, 6, "Route Corridor"),
        ("Canals Coffee Charge", -0.016, 0.021, 4, "Service Plaza"),
        ("Canals City Fast", 0.026, -0.019, 5, "City Hub"),
    ]
    base_id = abs(int(lat * 1000) * 100000 + int(lng * 1000))
    stations = [
        EvStation(
            id=base_id + index,
            name=name,
            lat=round(lat + d_lat, 6),
            lng=round(lng + d_lng, 6),
            connections=connections,
            town=town,
            country="DE",
        )
        for index, (name, d_lat, d_lng, connections, town) in enumerate(seeds[:max_results])
    ]
    return stations[:max_results]


@router.get("/ev-stations", response_model=list[EvStation], summary="Fetch EV charging stations near a coordinate")
async def get_ev_stations(lat: float, lng: float, radius_km: int = 10, max_results: int = 20):
    """Returns EV charging stations from OpenChargeMap near the given coordinate."""
    return await fetch_ev_stations(lat, lng, radius_km, max_results)


@router.get(
    "/route/ev-stations",
    response_model=list[EvStation],
    summary="Fetch EV stations along a route",
    tags=["Route", "EV"],
)
async def get_ev_stations_along_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float, radius_km: int = 10
):
    """Fetches the route waypoints, then queries EV stations near each waypoint. Returns deduplicated results."""
    route = await fetch_route(start_lat, start_lng, end_lat, end_lng)
    seen: set[int] = set()
    stations: list[EvStation] = []

    for wp in route.waypoints:
        for s in await fetch_ev_stations(wp.lat, wp.lng, radius_km=radius_km):
            if s.id not in seen:
                seen.add(s.id)
                stations.append(s)

    return stations
