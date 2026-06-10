from __future__ import annotations

import re
from typing import Set

from .models import CommandRequest, RouteLabel, RouterConstraints, RouterDecision

FAST_WORDS = {"fast", "rapid", "hpc", "ultra", "quick", "150", "250", "300", "350"}
CHARGER_WORDS = {"charger", "charging", "charge", "station", "plug"}
MAP_WORDS = {"map", "where are", "locations", "nearby", "around me", "show me"}
LIVE_WORDS = {
    "available",
    "availability",
    "right now",
    "currently",
    "live",
    "real-time",
    "realtime",
    "price now",
    "traffic",
    "web",
    "internet",
}
NAVIGATE_WORDS = {"navigate", "directions", "take me", "go there", "route me"}
PLAN_WORDS = {"plan", "drive", "trip", "journey", "route from", "from"}
LIGHT_WORDS = {"light", "lights", "headlight", "headlights", "beam"}
DEMO_WORDS = {
    "car demo",
    "demo sequence",
    "vehicle demo",
    "run the demo",
    "run demo",
    "show the car",
}


def decide_route(request: CommandRequest) -> RouterDecision:
    """Mock local model/policy. It is always called before cloud or cache work."""

    transcript = request.transcript.strip().lower()
    constraints = _extract_constraints(transcript, request.vehicle.connector)

    if not transcript:
        return RouterDecision(
            route=RouteLabel.clarify,
            intent="unknown",
            constraints=constraints,
            confidence=0.4,
            reason="No transcript was provided.",
        )

    if _contains_any(transcript, DEMO_WORDS):
        return RouterDecision(
            route=RouteLabel.local_simple,
            intent="vehicle_demo_sequence",
            constraints=constraints,
            confidence=0.9,
            reason="The Mini Demo Car sequence is a local vehicle action through the Car API.",
        )

    if _contains_any(transcript, NAVIGATE_WORDS):
        return RouterDecision(
            route=RouteLabel.local_simple,
            intent="navigate_selected_station",
            constraints=constraints,
            confidence=0.91,
            reason="Navigation to the previously selected cached station is a local action.",
        )

    if _contains_any(transcript, LIGHT_WORDS):
        if _contains_any(transcript, {"off", "disable", "turn off", "switch off"}):
            return RouterDecision(
                route=RouteLabel.local_simple,
                intent="lights_off",
                constraints=constraints,
                confidence=0.91,
                reason="Exterior lights are controlled through the local Car API.",
            )
        if _contains_any(transcript, {"on", "enable", "turn on", "switch on"}):
            return RouterDecision(
                route=RouteLabel.local_simple,
                intent="lights_on",
                constraints=constraints,
                confidence=0.91,
                reason="Exterior lights are controlled through the local Car API.",
            )

    origin, destination = _extract_journey_points(transcript)
    if origin and destination and _contains_any(transcript, PLAN_WORDS):
        return RouterDecision(
            route=RouteLabel.local_simple,
            requiresWeb=True,
            intent="plan_journey",
            origin=origin,
            destination=destination,
            constraints=constraints,
            confidence=0.84,
            reason="The user is planning a route; maps-api can build a local journey cache.",
        )

    requires_web = _contains_any(transcript, LIVE_WORDS)
    mentions_charging = _contains_any(transcript, CHARGER_WORDS) or "reach" in transcript
    mentions_map = _contains_any(transcript, MAP_WORDS)

    if requires_web and request.network.online:
        return RouterDecision(
            route=RouteLabel.cloud_required,
            requiresWeb=True,
            intent=_live_intent(transcript),
            constraints=constraints,
            confidence=0.9,
            reason="The request explicitly asks for live/current data and the network is online.",
        )

    if requires_web and not request.network.online:
        return RouterDecision(
            route=RouteLabel.offline_fallback,
            requiresWeb=True,
            intent=_live_intent(transcript),
            constraints=constraints,
            confidence=0.86,
            reason="The request needs live data, but the network is offline, so cached data must be used with a freshness warning.",
        )

    if mentions_charging or mentions_map:
        return RouterDecision(
            route=RouteLabel.local_cache_search,
            intent="find_charger_map" if mentions_map else "find_charger",
            constraints=constraints,
            confidence=0.92,
            reason="The request can be answered from cached charging station data.",
        )

    if any(word in transcript for word in ["battery", "range", "how far"]):
        return RouterDecision(
            route=RouteLabel.local_simple,
            intent="vehicle_status",
            constraints=constraints,
            confidence=0.88,
            reason="Vehicle battery and range are already present in local vehicle state.",
        )

    return RouterDecision(
        route=RouteLabel.unsupported,
        intent="unsupported",
        constraints=constraints,
        confidence=0.45,
        reason="The local router could not map the request to a supported vehicle charging action.",
    )


def _extract_constraints(transcript: str, vehicle_connector: str) -> RouterConstraints:
    min_kw = None
    kw_match = re.search(r"(\d{2,3})\s*(?:kw|kilowatt|kilowatts)", transcript)
    if kw_match:
        min_kw = int(kw_match.group(1))
    elif _contains_any(transcript, FAST_WORDS):
        min_kw = 150

    amenities = []
    for amenity in ["coffee", "restaurant", "restroom", "wifi", "shop", "shopping", "snacks"]:
        if amenity in transcript:
            amenities.append(amenity)

    min_arrival_battery = 5
    battery_match = re.search(r"(\d{1,2})\s*%\s*(?:arrival|when i arrive|left)", transcript)
    if battery_match:
        min_arrival_battery = int(battery_match.group(1))

    return RouterConstraints(
        minKw=min_kw,
        connector=vehicle_connector,
        amenities=amenities,
        minArrivalBatteryPercent=min_arrival_battery,
    )


def _contains_any(text: str, needles: Set[str]) -> bool:
    return any(needle in text for needle in needles)


def _live_intent(transcript: str) -> str:
    if "price" in transcript:
        return "check_live_pricing"
    if "traffic" in transcript:
        return "check_live_traffic"
    return "check_live_availability"


def _extract_journey_points(transcript: str) -> tuple[str | None, str | None]:
    match = re.search(r"\bfrom\s+(.+?)\s+(?:to|towards)\s+(.+)", transcript)
    if not match:
        match = re.search(r"\b(?:to|towards)\s+(.+?)\s+from\s+(.+)", transcript)
        if not match:
            return None, None
        destination = _clean_place(match.group(1))
        origin = _clean_place(match.group(2))
        return origin, destination

    origin = _clean_place(match.group(1))
    destination = _clean_place(match.group(2))
    return origin, destination


def _clean_place(value: str) -> str:
    value = re.sub(r"\b(with|using|and|please|today|tomorrow)\b.*$", "", value.strip())
    return value.strip(" .,")
