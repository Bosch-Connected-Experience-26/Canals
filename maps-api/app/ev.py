import httpx
from fastapi import APIRouter, HTTPException

from app.config import OCM_URL, OCM_API_KEY
from app.models import EvStation
from app.route import fetch_route

router = APIRouter(tags=["EV"])


async def fetch_ev_stations(
    lat: float, lng: float, radius_km: int = 10, max_results: int = 20
) -> list[EvStation]:
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
    if OCM_API_KEY:
        params["key"] = OCM_API_KEY

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OCM_URL, params=params)

    if resp.status_code != 200:
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
