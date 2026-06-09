from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from .cache import JourneyCacheStore
from .cloud import CloudGateway
from .config import load_settings
from .models import (
    CommandAction,
    CommandDebug,
    CommandRequest,
    CommandResponse,
    HealthResponse,
    JourneyCache,
    JourneyStartRequest,
    JourneyStartResponse,
    RouteLabel,
)
from .ranking import rank_stations
from .router import decide_route

app = FastAPI(
    title="Canals EV Voice Orchestrator",
    description="Offline-aware orchestration API for EV charging voice control.",
    version="0.1.0",
)
settings = load_settings()
store = JourneyCacheStore(settings)
cloud_gateway = CloudGateway(settings)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(cacheBackend=store.backend, cloudBackend=cloud_gateway.backend)


@app.post("/journey/start", response_model=JourneyStartResponse)
def start_journey(request: JourneyStartRequest) -> JourneyStartResponse:
    journey_id = request.journeyId or f"trip_{uuid4().hex[:8]}"
    cache = store.create_or_load(journey_id)
    return JourneyStartResponse(
        journeyId=journey_id,
        cache=cache,
        message=f"Journey {journey_id} is ready with {cache.metadata.stationCount} cached charging stations.",
    )


@app.get("/journey/{journey_id}/cache", response_model=JourneyCache)
def get_cache(journey_id: str) -> JourneyCache:
    cache = store.snapshot(journey_id)
    if not cache:
        raise HTTPException(status_code=404, detail="Journey cache not found. Start the journey first.")
    return cache


@app.post("/command", response_model=CommandResponse)
def command(request: CommandRequest) -> CommandResponse:
    cache = store.get(request.journeyId)
    if not cache:
        cache = store.create_or_load(request.journeyId)

    decision = decide_route(request)
    warnings: List[str] = []
    cloud_used = False
    stale_warning = None

    if cache.metadata.age_minutes >= 15:
        stale_warning = f"Cached charger data is {cache.metadata.age_minutes} minutes old."

    if decision.route == RouteLabel.local_simple:
        return _handle_local_simple(request, decision, cache)

    if decision.route in {RouteLabel.local_cache_search, RouteLabel.offline_fallback, RouteLabel.cloud_required}:
        if decision.route == RouteLabel.offline_fallback:
            stale_warning = stale_warning or "Live data is unavailable because the vehicle is offline; using cached availability."
            warnings.append(stale_warning)

        ranked = rank_stations(cache, decision.constraints, request.vehicle, stale_warning)

        if decision.route == RouteLabel.cloud_required and request.network.online:
            cloud_used = True
            ranked, cloud_warnings = cloud_gateway.enrich_live_availability(ranked)
            warnings.extend(cloud_warnings)

        if not ranked:
            spoken = "I could not find a reachable cached charger that matches those constraints."
            actions: List[CommandAction] = []
            selected = None
            alternatives = []
        else:
            selected = ranked[0]
            alternatives = ranked[1:4]
            store.set_last_selected(request.journeyId, selected.id)
            spoken = _spoken_station_response(selected, decision.route, stale_warning)
            actions = [
                CommandAction(
                    type="start_navigation",
                    stationId=selected.id,
                    label=f"Navigate to {selected.name}",
                    payload={"lat": selected.lat, "lng": selected.lng},
                )
            ]

        return CommandResponse(
            route=decision.route,
            spokenResponse=spoken,
            intent=decision.intent,
            selectedStation=selected,
            alternatives=alternatives,
            actions=actions,
            debug=_debug(decision, cache, cloud_used, warnings),
        )

    if decision.route == RouteLabel.clarify:
        return CommandResponse(
            route=decision.route,
            spokenResponse="What kind of charger should I look for?",
            intent=decision.intent,
            debug=_debug(decision, cache, False, warnings),
        )

    return CommandResponse(
        route=RouteLabel.unsupported,
        spokenResponse="I can help with EV charging search, charger availability, and navigation to a selected charger.",
        intent=decision.intent,
        debug=_debug(decision, cache, False, warnings),
    )


def _handle_local_simple(request: CommandRequest, decision, cache: JourneyCache) -> CommandResponse:
    if decision.intent == "navigate_selected_station":
        station = store.get_last_selected(request.journeyId)
        if not station:
            return CommandResponse(
                route=RouteLabel.clarify,
                spokenResponse="Which charging station should I navigate to?",
                intent=decision.intent,
                debug=_debug(decision, cache, False, ["No previously selected station."]),
            )
        return CommandResponse(
            route=RouteLabel.local_simple,
            spokenResponse=f"Starting navigation to {station.name}.",
            intent=decision.intent,
            selectedStation=station,
            actions=[
                CommandAction(
                    type="start_navigation",
                    stationId=station.id,
                    label=f"Navigate to {station.name}",
                    payload={"lat": station.lat, "lng": station.lng},
                )
            ],
            debug=_debug(decision, cache, False, []),
        )

    return CommandResponse(
        route=RouteLabel.local_simple,
        spokenResponse=(
            f"Your battery is at {round(request.vehicle.batteryPercent)} percent "
            f"with about {round(request.vehicle.rangeKm)} kilometers of range."
        ),
        intent=decision.intent,
        debug=_debug(decision, cache, False, []),
    )


def _spoken_station_response(station, route: RouteLabel, stale_warning: Optional[str]) -> str:
    prefix = ""
    if route == RouteLabel.cloud_required:
        prefix = "Using live availability, "
    elif route == RouteLabel.offline_fallback:
        prefix = "I cannot check live data right now, but from the cache, "

    amenity_text = ""
    if station.amenities:
        amenity_text = f" It has {', '.join(station.amenities[:3])}."

    warning_text = f" {stale_warning}" if stale_warning else ""
    return (
        f"{prefix}I recommend {station.name}, {round(station.distanceKm, 1)} kilometers away "
        f"with up to {station.maxKw} kilowatts and {station.cachedAvailability.status} availability cached."
        f"{amenity_text}{warning_text}"
    )


def _debug(decision, cache: JourneyCache, cloud_used: bool, warnings: List[str]) -> CommandDebug:
    return CommandDebug(
        cloudUsed=cloud_used,
        routeReason=decision.reason,
        cacheAgeMinutes=cache.metadata.age_minutes,
        cacheGeneratedAt=cache.metadata.generatedAt,
        cacheStationCount=cache.metadata.stationCount,
        warnings=warnings,
        routerDecision=decision,
    )
