import httpx
from fastapi import APIRouter, HTTPException

from app.config import NOMINATIM_URL
from app.models import Location

router = APIRouter(tags=["Geocode"])

_HEADERS = {"User-Agent": "canals-maps-api/0.1"}


async def geocode(location: str) -> Location:
    params = {"q": location, "format": "json", "limit": 1}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(NOMINATIM_URL, params=params, headers=_HEADERS)
    if resp.status_code != 200 or not resp.json():
        raise HTTPException(status_code=404, detail=f"Location not found: {location}")
    result = resp.json()[0]
    return Location(
        name=result.get("display_name", location),
        lat=float(result["lat"]),
        lng=float(result["lon"]),
    )


@router.get("/geocode", response_model=Location, summary="Geocode a location name to GPS coordinates")
async def geocode_location(location: str):
    """Converts a location name (e.g. 'Frankfurt') to GPS coordinates using Nominatim."""
    return await geocode(location)
