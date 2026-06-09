"""
E2E tests: Maps API — Frankfurt → Munich route
"""

import os
import pytest
import httpx

BASE = os.getenv("MAPS_API_URL", "http://maps-api:8000")

client = httpx.Client(timeout=30)


@pytest.fixture(scope="module")
def frankfurt():
    resp = client.get(f"{BASE}/geocode", params={"location": "Frankfurt"})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture(scope="module")
def munich():
    resp = client.get(f"{BASE}/geocode", params={"location": "Munich"})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture(scope="module")
def route(frankfurt, munich):
    resp = client.get(f"{BASE}/route/cities", params={"start": "Frankfurt", "end": "Munich"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_geocode_frankfurt(frankfurt):
    assert 49.0 < frankfurt["lat"] < 51.0
    assert 8.0 < frankfurt["lng"] < 9.5


def test_geocode_munich(munich):
    assert 47.0 < munich["lat"] < 49.0
    assert 11.0 < munich["lng"] < 12.5


def test_route_waypoints(route):
    assert len(route["waypoints"]) == 10
    assert route["distance_km"] > 300
    assert route["duration_min"] > 180


def test_route_waypoint_coords(route):
    for wp in route["waypoints"]:
        assert -90 <= wp["lat"] <= 90
        assert -180 <= wp["lng"] <= 180


def test_ev_stations_along_route(frankfurt, munich):
    resp = client.get(f"{BASE}/route/ev-stations", params={
        "start_lat": frankfurt["lat"],
        "start_lng": frankfurt["lng"],
        "end_lat":   munich["lat"],
        "end_lng":   munich["lng"],
        "radius_km": 10,
    })
    assert resp.status_code == 200
    stations = resp.json()
    assert len(stations) > 0
    for s in stations:
        assert s["lat"] != 0
        assert s["lng"] != 0
