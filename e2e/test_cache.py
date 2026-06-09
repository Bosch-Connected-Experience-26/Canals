"""
E2E tests: Cache Service — Frankfurt → Munich
"""

import os
import pytest
import httpx

BASE       = os.getenv("CACHE_SERVICE_URL", "http://cache-service:8002")
JOURNEY_ID = "e2e-frankfurt-munich"

client = httpx.Client(timeout=120)


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    client.delete(f"{BASE}/journey/{JOURNEY_ID}")
    yield
    client.delete(f"{BASE}/journey/{JOURNEY_ID}")


@pytest.fixture(scope="module")
def journey():
    resp = client.post(f"{BASE}/journey", json={
        "start": "Frankfurt",
        "end": "Munich",
        "journey_id": JOURNEY_ID,
        "radius_km": 10,
    })
    assert resp.status_code == 200, f"POST /journey failed: {resp.text}"
    return resp.json()


def test_journey_created(journey):
    assert journey["journey_id"] == JOURNEY_ID
    assert journey["status"] == "complete"
    assert journey["poi_count"] > 0, "Expected at least one POI cached"


def test_journey_status(journey):
    resp = client.get(f"{BASE}/journey/{JOURNEY_ID}")
    assert resp.status_code == 200
    assert resp.json()["poi_count"] == journey["poi_count"]


def test_list_pois(journey):
    resp = client.get(f"{BASE}/journey/{JOURNEY_ID}/pois")
    assert resp.status_code == 200
    pois = resp.json()
    assert len(pois) == journey["poi_count"]
    for p in pois:
        assert p["lat"] != 0
        assert p["lng"] != 0
        assert p["name"]


def test_filter_pois_by_type(journey):
    resp = client.get(f"{BASE}/journey/{JOURNEY_ID}/pois", params={"poi_type": "ev_charging"})
    assert resp.status_code == 200
    pois = resp.json()
    assert all(p["poi_type"] == "ev_charging" for p in pois)


def test_nearby_offline():
    resp = client.get(f"{BASE}/nearby", params={
        "lat": 50.1109,
        "lng": 8.6821,
        "radius_m": 15000,
    })
    assert resp.status_code == 200
    assert len(resp.json()) > 0, "Expected nearby EV stations in Frankfurt"


def test_journey_not_found():
    resp = client.get(f"{BASE}/journey/does-not-exist")
    assert resp.status_code == 404


def test_delete_journey(journey):
    resp = client.delete(f"{BASE}/journey/{JOURNEY_ID}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == journey["poi_count"]

    resp = client.get(f"{BASE}/journey/{JOURNEY_ID}")
    assert resp.status_code == 404
