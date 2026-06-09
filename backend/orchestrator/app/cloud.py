from __future__ import annotations

import json
from copy import deepcopy
from typing import List, Tuple

from .config import Settings
from .models import Station


class CloudGateway:
    """Cloud service adapter. Uses AWS Bedrock when enabled, otherwise a mock."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backend = "aws_bedrock" if settings.aws_bedrock_enabled else "mock"

    def enrich_live_availability(self, stations: List[Station]) -> Tuple[List[Station], List[str]]:
        if self.settings.aws_bedrock_enabled:
            try:
                return self._enrich_with_bedrock(stations), []
            except Exception as exc:
                return _enrich_with_live_mock(stations), [
                    f"AWS Bedrock unavailable, used deterministic cloud mock: {exc.__class__.__name__}."
                ]

        return _enrich_with_live_mock(stations), []

    def _enrich_with_bedrock(self, stations: List[Station]) -> List[Station]:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("boto3 is not installed") from exc

        client = boto3.client("bedrock-runtime", region_name=self.settings.aws_region)
        station_payload = [
            {
                "id": station.id,
                "name": station.name,
                "cachedAvailability": station.cachedAvailability.model_dump(mode="json"),
                "reliability": station.reliability,
            }
            for station in stations[:5]
        ]
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Return JSON only. For each EV charger, estimate live availability "
                        "as high, medium, low, or unknown using cached availability and reliability. "
                        f"Stations: {json.dumps(station_payload)}"
                    ),
                }
            ],
        }
        response = client.invoke_model(
            modelId=self.settings.aws_bedrock_model_id,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        parsed = json.loads(response["body"].read())
        text = parsed["content"][0]["text"]
        updates = {item["id"]: item for item in json.loads(text).get("stations", [])}

        enriched = deepcopy(stations)
        for station in enriched:
            update = updates.get(station.id)
            if not update:
                continue
            station.cachedAvailability.source = "aws_bedrock"
            station.cachedAvailability.status = update.get("status", station.cachedAvailability.status)
            if "availableStalls" in update:
                station.cachedAvailability.availableStalls = update["availableStalls"]
            station.matchReasons.insert(0, "AWS Bedrock estimated live availability")
        return enriched


def _enrich_with_live_mock(stations: List[Station]) -> List[Station]:
    """Deterministic placeholder for cloud/live availability."""

    enriched: List[Station] = []
    for index, station in enumerate(stations):
        updated = deepcopy(station)
        updated.cachedAvailability.source = "live_mock"
        if index == 0:
            updated.cachedAvailability.status = "high"
            updated.cachedAvailability.availableStalls = max(
                updated.cachedAvailability.availableStalls or 0,
                3,
            )
            updated.matchReasons.insert(0, "live mock confirms strong availability")
        enriched.append(updated)
    return enriched
