from pydantic import BaseModel


class Coordinate(BaseModel):
    lat: float
    lng: float


class Location(BaseModel):
    name: str
    lat: float
    lng: float


class RouteResponse(BaseModel):
    waypoints: list[Coordinate]
    distance_km: float
    duration_min: float


class EvStation(BaseModel):
    id: int
    name: str
    lat: float
    lng: float
    connections: int
    town: str | None = None
    country: str | None = None
