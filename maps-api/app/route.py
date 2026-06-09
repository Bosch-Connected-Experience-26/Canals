import httpx
from fastapi import APIRouter, HTTPException

from app.config import OSRM_URL
from app.geocode import geocode
from app.models import Coordinate, RouteResponse

router = APIRouter(tags=["Route"])


def sample_waypoints(coordinates: list[list[float]], n: int = 10) -> list[Coordinate]:
    """Sample n evenly spaced points from a list of [lng, lat] coordinates."""
    if len(coordinates) <= n:
        return [Coordinate(lat=c[1], lng=c[0]) for c in coordinates]
    step = (len(coordinates) - 1) / (n - 1)
    return [
        Coordinate(lat=coordinates[round(i * step)][1], lng=coordinates[round(i * step)][0])
        for i in range(n)
    ]


async def fetch_route(
    start_lat: float, start_lng: float, end_lat: float, end_lng: float
) -> RouteResponse:
    url    = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
    params = {"overview": "full", "geometries": "geojson"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="OSRM request failed")

    data = resp.json()
    if not data.get("routes"):
        raise HTTPException(status_code=404, detail="No route found")

    route = data["routes"][0]
    return RouteResponse(
        waypoints=sample_waypoints(route["geometry"]["coordinates"], n=10),
        distance_km=round(route["distance"] / 1000, 2),
        duration_min=round(route["duration"] / 60, 2),
    )


@router.get("/route", response_model=RouteResponse, summary="Get 10 GPS waypoints between two locations")
async def get_route(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    """Fetches a road-accurate route from OSRM and returns 10 evenly sampled GPS waypoints."""
    return await fetch_route(start_lat, start_lng, end_lat, end_lng)


@router.get("/route/cities", response_model=RouteResponse, summary="Get 10 GPS waypoints between two city names")
async def get_route_by_cities(start: str, end: str):
    """Geocodes two city names, then returns 10 road-accurate GPS waypoints between them."""
    start_loc = await geocode(start)
    end_loc   = await geocode(end)
    return await fetch_route(start_loc.lat, start_loc.lng, end_loc.lat, end_loc.lng)
