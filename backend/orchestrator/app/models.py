from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RouteLabel(str, Enum):
    local_simple = "local_simple"
    local_cache_search = "local_cache_search"
    cloud_required = "cloud_required"
    cloud_optional = "cloud_optional"
    offline_fallback = "offline_fallback"
    clarify = "clarify"
    unsupported = "unsupported"


class NetworkState(BaseModel):
    online: bool = True
    latencyMs: Optional[int] = Field(default=None, ge=0)


class VehicleState(BaseModel):
    batteryPercent: float = Field(ge=0, le=100)
    rangeKm: float = Field(ge=0)
    lat: float
    lng: float
    connector: str = "CCS"


class RoutePoint(BaseModel):
    lat: float
    lng: float
    label: Optional[str] = None


class JourneyStartRequest(BaseModel):
    journeyId: Optional[str] = None
    origin: Optional[RoutePoint] = None
    destination: Optional[RoutePoint] = None
    vehicle: Optional[VehicleState] = None


class StationAvailability(BaseModel):
    status: Literal["high", "medium", "low", "unknown"]
    availableStalls: Optional[int] = Field(default=None, ge=0)
    totalStalls: Optional[int] = Field(default=None, ge=0)
    source: Literal["cached", "maps_api", "live_mock", "aws_bedrock"] = "cached"


class Station(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    distanceKm: float
    detourKm: float
    maxKw: int
    connectors: List[str]
    amenities: List[str] = []
    reliability: float = Field(ge=0, le=1)
    cachedAvailability: StationAvailability
    priceEurPerKwh: Optional[float] = Field(default=None, ge=0)
    reachableWithCurrentRange: bool = True
    estimatedArrivalBatteryPercent: Optional[float] = None
    score: Optional[float] = None
    matchReasons: List[str] = []
    warnings: List[str] = []


class CacheMetadata(BaseModel):
    journeyId: str
    generatedAt: datetime
    stationCount: int
    source: str = "mock_route_cache"

    @property
    def age_minutes(self) -> int:
        now = datetime.now(timezone.utc)
        generated = self.generatedAt
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
        return max(0, int((now - generated).total_seconds() // 60))


class JourneyCache(BaseModel):
    metadata: CacheMetadata
    stations: List[Station]
    lastSelectedStationId: Optional[str] = None


class CommandRequest(BaseModel):
    journeyId: str
    transcript: str
    network: NetworkState
    vehicle: VehicleState


class RouterConstraints(BaseModel):
    minKw: Optional[int] = None
    connector: Optional[str] = None
    amenities: List[str] = []
    minArrivalBatteryPercent: float = 10


class RouterDecision(BaseModel):
    route: RouteLabel
    requiresWeb: bool = False
    intent: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    constraints: RouterConstraints = Field(default_factory=RouterConstraints)
    confidence: float = Field(ge=0, le=1)
    reason: str


class CommandAction(BaseModel):
    type: str
    stationId: Optional[str] = None
    label: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


class CommandDebug(BaseModel):
    cloudUsed: bool
    routeReason: str
    cacheAgeMinutes: Optional[int] = None
    cacheGeneratedAt: Optional[datetime] = None
    cacheStationCount: Optional[int] = None
    warnings: List[str] = []
    routerDecision: RouterDecision


class CommandResponse(BaseModel):
    route: RouteLabel
    spokenResponse: str
    intent: str
    selectedStation: Optional[Station] = None
    alternatives: List[Station] = []
    actions: List[CommandAction] = []
    debug: CommandDebug


class JourneyStartResponse(BaseModel):
    journeyId: str
    cache: JourneyCache
    message: str


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "canals-orchestrator"
    version: str = "0.1.0"
    cacheBackend: str = "unknown"
    cloudBackend: str = "mock"
