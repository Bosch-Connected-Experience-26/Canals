from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import Settings
from .models import CacheMetadata, JourneyCache, Station

DATA_PATH = Path(__file__).parent / "data" / "mock_stations.json"


class JourneyCacheStore:
    """Journey cache store that prefers MongoDB and falls back to memory for demos."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._journeys: Dict[str, JourneyCache] = {}
        self._collection = self._connect_mongo(settings)
        self.backend = "mongodb" if self._collection is not None else "memory_fallback"

    def create_or_load(self, journey_id: str) -> JourneyCache:
        existing = self.get(journey_id)
        if existing:
            return existing

        with DATA_PATH.open("r", encoding="utf-8") as handle:
            raw_stations = json.load(handle)

        stations = [Station.model_validate(item) for item in raw_stations]
        cache = JourneyCache(
            metadata=CacheMetadata(
                journeyId=journey_id,
                generatedAt=datetime.now(timezone.utc),
                stationCount=len(stations),
            ),
            stations=stations,
        )
        self._save(cache)
        return cache

    def get(self, journey_id: str) -> Optional[JourneyCache]:
        if self._collection is not None:
            document = self._collection.find_one({"_id": journey_id})
            if document:
                return JourneyCache.model_validate(document["cache"])
        return self._journeys.get(journey_id)

    def set_last_selected(self, journey_id: str, station_id: str) -> None:
        cache = self.get(journey_id)
        if not cache:
            return
        cache.lastSelectedStationId = station_id
        self._save(cache)

    def get_last_selected(self, journey_id: str) -> Optional[Station]:
        cache = self.get(journey_id)
        if not cache or not cache.lastSelectedStationId:
            return None
        return next(
            (station for station in cache.stations if station.id == cache.lastSelectedStationId),
            None,
        )

    def snapshot(self, journey_id: str) -> Optional[JourneyCache]:
        cache = self.get(journey_id)
        return deepcopy(cache) if cache else None

    def _save(self, cache: JourneyCache) -> None:
        self._journeys[cache.metadata.journeyId] = cache
        if self._collection is not None:
            self._collection.replace_one(
                {"_id": cache.metadata.journeyId},
                {"_id": cache.metadata.journeyId, "cache": cache.model_dump(mode="json")},
                upsert=True,
            )

    def _connect_mongo(self, settings: Settings) -> Optional[Any]:
        try:
            from pymongo import MongoClient
        except ImportError:
            return None

        try:
            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=500)
            client.admin.command("ping")
            database = client[settings.mongodb_database]
            collection = database[settings.mongodb_collection]
            collection.create_index("cache.metadata.generatedAt")
            return collection
        except Exception:
            return None
