"""
E2E tests: Car API — lights on/off via KUKSA mock
"""

import os
import httpx
import pytest

BASE = os.getenv("CAR_API_URL", "http://car-api:8003")

client = httpx.Client(timeout=15)


def test_lights_on():
    resp = client.post(f"{BASE}/lights/on")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["vehicle"]


def test_lights_off():
    resp = client.post(f"{BASE}/lights/off")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["vehicle"]
