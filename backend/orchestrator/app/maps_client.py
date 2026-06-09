from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

from .config import Settings
from .models import CacheMetadata, JourneyCache, Station, StationAvailability, VehicleState


class MapsApiClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.maps_api_base_url.rstrip("/")

    def build_journey_cache(
        self,
        journey_id: str,
        origin: str,
        destination: str,
        vehicle: VehicleState,
    ) -> JourneyCache:
        with httpx.Client(timeout=20) as client:
            origin_loc = _get(client, f"{self.base_url}/geocode", {"location": origin})
            destination_loc = _get(client, f"{self.base_url}/geocode", {"location": destination})
            raw_stations = _get(
                client,
                f"{self.base_url}/route/ev-stations",
                {
                    "start_lat": origin_loc["lat"],
                    "start_lng": origin_loc["lng"],
                    "end_lat": destination_loc["lat"],
                    "end_lng": destination_loc["lng"],
                    "radius_km": 10,
                },
            )

        stations = _stations_from_maps(raw_stations, vehicle)
        return JourneyCache(
            metadata=CacheMetadata(
                journeyId=journey_id,
                generatedAt=datetime.now(timezone.utc),
                stationCount=len(stations),
                source="maps_api",
            ),
            stations=stations,
        )


def _get(client: httpx.Client, url: str, params: dict[str, Any]) -> Any:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def _stations_from_maps(raw_stations: Iterable[dict[str, Any]], vehicle: VehicleState) -> list[Station]:
    stations: list[Station] = []
    for index, item in enumerate(raw_stations):
        station_id = str(item.get("id") or f"maps-{index}")
        distance_km = _distance_km(vehicle.lat, vehicle.lng, float(item["lat"]), float(item["lng"]))
        connections = max(1, int(item.get("connections") or 1))
        amenities = _synthetic_amenities(station_id, index)
        max_kw = 150 if connections >= 3 else 50
        stations.append(
            Station(
                id=f"maps-{station_id}",
                name=item.get("name") or "EV charging station",
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                distanceKm=round(distance_km, 2),
                detourKm=round(min(12, 1.5 + (index % 5) * 1.3), 1),
                maxKw=max_kw,
                connectors=[vehicle.connector, "Type 2"],
                amenities=amenities,
                reliability=round(0.72 + ((index % 5) * 0.045), 2),
                cachedAvailability=StationAvailability(
                    status="unknown",
                    availableStalls=None,
                    totalStalls=connections,
                    source="maps_api",
                ),
                priceEurPerKwh=round(0.45 + ((index % 4) * 0.04), 2),
            )
        )
    return stations


def _synthetic_amenities(station_id: str, index: int) -> list[str]:
    amenities = [["coffee", "restroom"], ["shop"], ["restaurant"], ["wifi", "snacks"]]
    try:
        bucket = (int(station_id) + index) % len(amenities)
    except ValueError:
        bucket = index % len(amenities)
    return amenities[bucket]


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
