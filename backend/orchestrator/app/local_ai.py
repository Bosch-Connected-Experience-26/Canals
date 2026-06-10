from __future__ import annotations

import json
from typing import Any

import httpx

from .config import Settings
from .models import CommandRequest, RouteLabel, RouterDecision
from .router import decide_route

SUPPORTED_INTENTS = {
    "plan_journey",
    "find_charger",
    "check_live_availability",
    "check_live_pricing",
    "check_live_traffic",
    "navigate_selected_station",
    "vehicle_status",
    "lights_on",
    "lights_off",
    "unsupported",
    "unknown",
}


class LocalAIRouter:
    """Local Ollama classifier with deterministic rule-router fallback."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backend = "ollama" if settings.use_ollama_router else "rules"

    def decide(self, request: CommandRequest) -> RouterDecision:
        fallback = decide_route(request)
        if not self.settings.use_ollama_router:
            return fallback

        try:
            decision = self._decide_with_ollama(request)
        except Exception as exc:
            fallback.reason = f"{fallback.reason} Ollama fallback: {exc.__class__.__name__}."
            return fallback

        return self._apply_network_policy(decision, request, fallback)

    def _decide_with_ollama(self, request: CommandRequest) -> RouterDecision:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
            "prompt": _prompt(request),
        }
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        with httpx.Client(timeout=self.settings.ollama_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

        body = response.json()
        raw = body.get("response", "")
        parsed = _loads_json_object(raw)
        decision = RouterDecision.model_validate(parsed)
        if decision.intent not in SUPPORTED_INTENTS:
            raise ValueError(f"unsupported intent from ollama: {decision.intent}")
        return decision

    def _apply_network_policy(
        self,
        decision: RouterDecision,
        request: CommandRequest,
        fallback: RouterDecision,
    ) -> RouterDecision:
        if decision.intent == "plan_journey":
            if not decision.origin or not decision.destination:
                return fallback
            decision.route = RouteLabel.local_simple
            decision.requiresWeb = True
            return decision

        if decision.intent in {"find_charger"}:
            decision.route = RouteLabel.local_cache_search
            decision.requiresWeb = False
            if not decision.constraints.connector:
                decision.constraints.connector = request.vehicle.connector
            return decision

        if decision.intent in {"check_live_availability", "check_live_pricing", "check_live_traffic"}:
            decision.requiresWeb = True
            decision.route = RouteLabel.cloud_required if request.network.online else RouteLabel.offline_fallback
            if not decision.constraints.connector:
                decision.constraints.connector = request.vehicle.connector
            return decision

        if decision.intent in {"navigate_selected_station", "vehicle_status", "lights_on", "lights_off"}:
            decision.route = RouteLabel.local_simple
            decision.requiresWeb = False
            return decision

        if decision.intent in {"unknown"}:
            decision.route = RouteLabel.clarify
            return decision

        return decision


def _prompt(request: CommandRequest) -> str:
    return f"""
You are a local in-vehicle EV assistant router. Classify and extract only.
Return one JSON object only. Do not execute actions. Do not call tools.

Allowed routes:
- local_simple
- local_cache_search
- cloud_required
- cloud_optional
- offline_fallback
- clarify
- unsupported

Allowed intents:
- plan_journey
- find_charger
- check_live_availability
- check_live_pricing
- check_live_traffic
- navigate_selected_station
- vehicle_status
- lights_on
- lights_off
- unsupported
- unknown

Policy:
- Simple vehicle or navigation commands are local_simple.
- Turning exterior lights on or off is local_simple with intent lights_on or lights_off.
- Charger searches answerable from cached stations are local_cache_search.
- Explicit live/current availability, live price, traffic, web, or internet requests require live data.
- If live data is requested and networkOnline is false, use offline_fallback.
- Journey planning from one place to another is intent plan_journey with route local_simple and requiresWeb true because the orchestrator will call maps-api.
- Extract origin and destination as plain place names for journey planning.
- Extract constraints only: connector, minKw, amenities, minArrivalBatteryPercent.

Return this exact JSON shape:
{{
  "intent": "find_charger",
  "route": "local_cache_search",
  "requiresWeb": false,
  "origin": null,
  "destination": null,
  "constraints": {{
    "connector": "{request.vehicle.connector}",
    "minKw": null,
    "amenities": [],
  "minArrivalBatteryPercent": 5
  }},
  "confidence": 0.0,
  "reason": "short reason"
}}

Transcript: {request.transcript!r}
networkOnline: {request.network.online}
vehicleConnector: {request.vehicle.connector!r}
vehicleRangeKm: {request.vehicle.rangeKm}
""".strip()


def _loads_json_object(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(raw[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("ollama response was not a JSON object")
    return parsed
