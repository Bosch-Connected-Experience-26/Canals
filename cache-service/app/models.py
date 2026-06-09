from typing import Optional

from pydantic import BaseModel


class JourneyRequest(BaseModel):
    start: str
    end: str
    journey_id: Optional[str] = None
    radius_km: int = 10


class JourneyStatus(BaseModel):
    journey_id: str
    start: str
    end: str
    poi_count: int
    status: str
    created_at: str


class PoiSummary(BaseModel):
    source_id: str
    poi_type: str
    name: str
    lat: float
    lng: float
    town: Optional[str]
    country: Optional[str]
    connections: int


class NearestPoi(PoiSummary):
    distance_m: float
