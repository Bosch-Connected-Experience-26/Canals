from __future__ import annotations

from copy import deepcopy
from typing import List, Optional

from .models import JourneyCache, RouterConstraints, Station, VehicleState

AVAILABILITY_SCORE = {
    "high": 1.0,
    "medium": 0.65,
    "low": 0.25,
    "unknown": 0.35,
}


def rank_stations(
    cache: JourneyCache,
    constraints: RouterConstraints,
    vehicle: VehicleState,
    stale_warning: Optional[str] = None,
) -> List[Station]:
    ranked: List[Station] = []

    for source_station in cache.stations:
        station = deepcopy(source_station)
        station.estimatedArrivalBatteryPercent = max(
            0,
            vehicle.batteryPercent - (station.distanceKm / max(vehicle.rangeKm, 1)) * vehicle.batteryPercent,
        )
        station.reachableWithCurrentRange = (
            station.distanceKm <= vehicle.rangeKm
            and station.estimatedArrivalBatteryPercent >= constraints.minArrivalBatteryPercent
        )

        connector = (constraints.connector or vehicle.connector).upper()
        if connector not in {item.upper() for item in station.connectors}:
            continue
        if not station.reachableWithCurrentRange:
            continue
        if constraints.minKw and station.maxKw < constraints.minKw:
            continue

        amenity_matches = len(
            {amenity.lower() for amenity in station.amenities}
            & {amenity.lower() for amenity in constraints.amenities}
        )
        missing_amenities = sorted(
            {amenity.lower() for amenity in constraints.amenities}
            - {amenity.lower() for amenity in station.amenities}
        )

        station.score = _score_station(station, amenity_matches, len(constraints.amenities))
        station.matchReasons = _match_reasons(station, constraints, amenity_matches, missing_amenities)
        if stale_warning:
            station.warnings.append(stale_warning)
        ranked.append(station)

    return sorted(ranked, key=lambda item: item.score or 0, reverse=True)


def _score_station(station: Station, amenity_matches: int, requested_amenities: int) -> float:
    availability = AVAILABILITY_SCORE[station.cachedAvailability.status]
    speed = min(station.maxKw / 350, 1.0)
    distance = max(0, 1 - (station.distanceKm / 160))
    detour = max(0, 1 - (station.detourKm / 15))
    amenity = amenity_matches / requested_amenities if requested_amenities else 0.5
    price = 0.5
    if station.priceEurPerKwh is not None:
        price = max(0, min(1, 1 - ((station.priceEurPerKwh - 0.35) / 0.4)))

    return round(
        station.reliability * 0.28
        + availability * 0.22
        + speed * 0.18
        + distance * 0.14
        + detour * 0.08
        + amenity * 0.07
        + price * 0.03,
        4,
    )


def _match_reasons(
    station: Station,
    constraints: RouterConstraints,
    amenity_matches: int,
    missing_amenities: List[str],
) -> List[str]:
    reasons = [
        f"{station.maxKw} kW charging",
        f"{station.cachedAvailability.status} cached availability",
        f"{round(station.detourKm, 1)} km detour",
        f"{round(station.reliability * 100)}% reliability",
    ]
    if constraints.amenities and amenity_matches:
        reasons.append(f"matches {amenity_matches} requested amenity")
    if missing_amenities:
        reasons.append(f"missing: {', '.join(missing_amenities)}")
    return reasons
