from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import math

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

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
OCM_URL = "https://api.openchargemap.io/v3/poi/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


class Coordinate(BaseModel):
    lat: float
    lng: float

class Location(BaseModel):
    name: str
    lat: float
    lng: float


class RouteResponse(BaseModel):
    waypoints: list[Coordinate]
    distance_km: float
    duration_min: float


class EvStation(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    connections: int


async def geocode(location: str) -> Location:
    params = {"q": location, "format": "json", "limit": 1}
    headers = {"User-Agent": "canals-maps-api/0.1"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=headers)
    if resp.status_code != 200 or not resp.json():
        raise HTTPException(status_code=404, detail=f"Location not found: {location}")
    result = resp.json()[0]
    return Location(name=result.get("display_name", location), lat=float(result["lat"]), lng=float(result["lon"]))


@app.get(
    "/geocode",
    response_model=Location,
    summary="Geocode a location name to GPS coordinates",
    tags=["Geocode"],
)
async def geocode_location(location: str):
    """
    Converts a location name (e.g. 'Frankfurt') to GPS coordinates using Nominatim.
    """
    return await geocode(location)


@app.get(
    "/route/cities",
    response_model=RouteResponse,
    summary="Get 10 GPS waypoints between two city names",
    tags=["Route"],
)
async def get_route_by_cities(start: str, end: str):
    """
    Geocodes two city names, then returns 10 road-accurate GPS waypoints between them.
    """
    start_loc = await geocode(start)
    end_loc = await geocode(end)
    return await get_route(start_loc.lat, start_loc.lng, end_loc.lat, end_loc.lng)


def sample_waypoints(coordinates: list[list[float]], n: int = 10) -> list[Coordinate]:
    """Sample n evenly spaced points from a list of [lng, lat] coordinates."""
    if len(coordinates) <= n:
        return [Coordinate(lat=c[1], lng=c[0]) for c in coordinates]
    step = (len(coordinates) - 1) / (n - 1)
    return [
        Coordinate(lat=coordinates[round(i * step)][1], lng=coordinates[round(i * step)][0])
        for i in range(n)
    ]


@app.get(
    "/route",
    response_model=RouteResponse,
    summary="Get 10 GPS waypoints between two locations",
    tags=["Route"],
)
async def get_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
):
    """
    Fetches a road-accurate route from OSRM and returns 10 evenly sampled GPS waypoints.
    """
    url = f"{OSRM_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
    params = {"overview": "full", "geometries": "geojson"}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="OSRM request failed")

    data = resp.json()
    if not data.get("routes"):
        raise HTTPException(status_code=404, detail="No route found")

    route = data["routes"][0]
    coordinates = route["geometry"]["coordinates"]
    distance_km = route["distance"] / 1000
    duration_min = route["duration"] / 60

    return RouteResponse(
        waypoints=sample_waypoints(coordinates, n=10),
        distance_km=round(distance_km, 2),
        duration_min=round(duration_min, 2),
    )


@app.get(
    "/ev-stations",
    response_model=list[EvStation],
    summary="Fetch EV charging stations near a coordinate",
    tags=["EV"],
)
async def get_ev_stations(
    lat: float,
    lng: float,
    radius_km: int = 10,
    max_results: int = 20,
):
    """
    Returns EV charging stations from OpenChargeMap near the given coordinate.
    """
    params = {
        "output": "json",
        "latitude": lat,
        "longitude": lng,
        "distance": radius_km,
        "distanceunit": "KM",
        "maxresults": max_results,
        "compact": "true",
        "verbose": "false",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(OCM_URL, params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="OpenChargeMap request failed")

    stations = []
    for poi in resp.json():
        addr = poi.get("AddressInfo", {})
        stations.append(EvStation(
            id=poi.get("ID", 0),
            name=addr.get("Title", "Unknown"),
            lat=addr.get("Latitude", 0.0),
            lng=addr.get("Longitude", 0.0),
            connections=len(poi.get("Connections") or []),
        ))

    return stations


@app.get(
    "/route/ev-stations",
    response_model=list[EvStation],
    summary="Fetch EV stations along a route",
    tags=["Route", "EV"],
)
async def get_ev_stations_along_route(
    start_lat: float,
    start_lng: float,
    end_lat: float,
    end_lng: float,
    radius_km: int = 10,
):
    """
    Fetches the route waypoints, then queries EV stations near each waypoint.
    Returns deduplicated results.
    """
    route = await get_route(start_lat, start_lng, end_lat, end_lng)
    seen: set[int] = set()
    stations: list[EvStation] = []

    for wp in route.waypoints:
        nearby = await get_ev_stations(wp.lat, wp.lng, radius_km=radius_km)
        for s in nearby:
            if s.id not in seen:
                seen.add(s.id)
                stations.append(s)

    return stations
