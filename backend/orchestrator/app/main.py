from __future__ import annotations

import os
import tempfile
from typing import List, Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .car_client import CarApiClient
from .cache import JourneyCacheStore
from .cloud import CloudGateway
from .config import load_settings
from .local_ai import LocalAIRouter
from .maps_client import MapsApiClient
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

app = FastAPI(
    title="Canals EV Voice Orchestrator",
    description="Offline-aware orchestration API for EV charging voice control.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
settings = load_settings()
store = JourneyCacheStore(settings)
cloud_gateway = CloudGateway(settings)
local_router = LocalAIRouter(settings)
maps_client = MapsApiClient(settings)
car_client = CarApiClient(settings)


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

    decision = local_router.decide(request)
    warnings: List[str] = []
    cloud_used = False
    stale_warning = None

    if cache.metadata.age_minutes >= 15:
        stale_warning = f"Cached charger data is {cache.metadata.age_minutes} minutes old."

    if decision.intent == "plan_journey":
        return _handle_plan_journey(request, decision, cache)

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

        _MAP_TRIGGERS = ("map", "where are", "locations", "nearby", "around me", "show me")
        wants_map = any(w in request.transcript.lower() for w in _MAP_TRIGGERS)

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
            if wants_map:
                actions.append(CommandAction(type="show_map", label="Show charger map"))

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


def _handle_plan_journey(request: CommandRequest, decision, cache: JourneyCache) -> CommandResponse:
    if not decision.origin or not decision.destination:
        return CommandResponse(
            route=RouteLabel.clarify,
            spokenResponse="Where should I plan the journey from and to?",
            intent=decision.intent,
            debug=_debug(decision, cache, False, ["Missing origin or destination."]),
        )

    warnings: List[str] = []
    cloud_used = False
    try:
        cache = maps_client.build_journey_cache(
            journey_id=request.journeyId,
            origin=decision.origin,
            destination=decision.destination,
            vehicle=request.vehicle,
        )
        store.replace(cache)
    except Exception as exc:
        warnings.append(
            f"maps-api was unavailable, so I kept the existing local cache: {exc.__class__.__name__}."
        )

    spoken = (
        f"I planned the journey from {decision.origin} to {decision.destination} "
        f"and cached {cache.metadata.stationCount} charging stations for offline use."
    )
    return CommandResponse(
        route=RouteLabel.local_simple,
        spokenResponse=spoken,
        intent=decision.intent,
        actions=[
            CommandAction(
                type="journey_cache_created",
                label="Cached charging stations",
                payload={
                    "journeyId": request.journeyId,
                    "origin": decision.origin,
                    "destination": decision.destination,
                    "stationCount": cache.metadata.stationCount,
                    "source": cache.metadata.source,
                },
            )
        ],
        debug=_debug(decision, cache, cloud_used, warnings),
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

    if decision.intent in {"lights_on", "lights_off"}:
        return _handle_lights_command(decision, cache)

    return CommandResponse(
        route=RouteLabel.local_simple,
        spokenResponse=(
            f"Your battery is at {round(request.vehicle.batteryPercent)} percent "
            f"with about {round(request.vehicle.rangeKm)} kilometers of range."
        ),
        intent=decision.intent,
        debug=_debug(decision, cache, False, []),
    )


def _handle_lights_command(decision, cache: JourneyCache) -> CommandResponse:
    enabled = decision.intent == "lights_on"
    action_type = "vehicle_lights_on" if enabled else "vehicle_lights_off"
    label = "Turn lights on" if enabled else "Turn lights off"
    warnings: List[str] = []
    payload = {"requestedState": "on" if enabled else "off"}

    try:
        payload["carApi"] = car_client.set_lights(enabled)
        spoken = "Turning the lights on." if enabled else "Turning the lights off."
    except Exception as exc:
        warnings.append(f"Car API unavailable: {exc.__class__.__name__}.")
        spoken = "I understood the lights command, but I could not reach the car API."

    return CommandResponse(
        route=RouteLabel.local_simple,
        spokenResponse=spoken,
        intent=decision.intent,
        actions=[
            CommandAction(
                type=action_type,
                label=label,
                payload=payload,
            )
        ],
        debug=_debug(decision, cache, False, warnings),
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


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    """Transcribe audio using OpenAI Whisper. Requires OPENAI_API_KEY env var."""
    try:
        import openai  # lazy import — gracefully absent if not installed

        audio_bytes = await file.read()
        suffix = os.path.splitext(file.filename or "audio.webm")[1] or ".webm"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            client = openai.OpenAI()
            with open(tmp_path, "rb") as f:
                result = client.audio.transcriptions.create(model="whisper-1", file=f)
        finally:
            os.unlink(tmp_path)

        return {"text": result.text}
    except ImportError:
        raise HTTPException(status_code=501, detail="openai package not installed. Run: pip install openai")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
