from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.models import CacheMetadata, JourneyCache, Station, StationAvailability
from app.main import app

client = TestClient(app)

VEHICLE = {
    "batteryPercent": 34,
    "rangeKm": 145,
    "lat": 52.52,
    "lng": 13.405,
    "connector": "CCS",
}


def post_command(transcript: str, online: bool = True):
    return client.post(
        "/command",
        json={
            "journeyId": "trip_test",
            "transcript": transcript,
            "network": {"online": online, "latencyMs": 80 if online else None},
            "vehicle": VEHICLE,
        },
    )


def test_journey_start_and_cache_debug():
    response = client.post("/journey/start", json={"journeyId": "trip_test"})
    assert response.status_code == 200
    assert response.json()["journeyId"] == "trip_test"
    assert response.json()["cache"]["metadata"]["stationCount"] >= 1

    cache_response = client.get("/journey/trip_test/cache")
    assert cache_response.status_code == 200
    assert len(cache_response.json()["stations"]) >= 1


def test_fast_charger_with_coffee_uses_local_cache_even_online():
    response = post_command("Find a fast charger with coffee", online=True)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_cache_search"
    assert body["debug"]["cloudUsed"] is False
    assert body["selectedStation"]["maxKw"] >= 150
    assert "coffee" in body["selectedStation"]["amenities"]


def test_live_availability_uses_cloud_when_online():
    response = post_command("Check live availability", online=True)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "cloud_required"
    assert body["debug"]["cloudUsed"] is True
    assert body["selectedStation"]["cachedAvailability"]["source"] == "live_mock"


def test_plan_journey_uses_maps_api_and_updates_cache(monkeypatch: pytest.MonkeyPatch):
    from app import main

    def fake_build_journey_cache(journey_id, origin, destination, vehicle):
        return JourneyCache(
            metadata=CacheMetadata(
                journeyId=journey_id,
                generatedAt=datetime.now(timezone.utc),
                stationCount=1,
                source="maps_api",
            ),
            stations=[
                    Station(
                        id="maps-demo",
                        name="Mapped Demo Charger",
                        lat=52.535,
                        lng=13.42,
                        distanceKm=42,
                        detourKm=2,
                        maxKw=150,
                    connectors=["CCS"],
                    amenities=["coffee"],
                    reliability=0.9,
                    cachedAvailability=StationAvailability(status="unknown", source="maps_api"),
                    reachableWithCurrentRange=True,
                )
            ],
        )

    monkeypatch.setattr(main.maps_client, "build_journey_cache", fake_build_journey_cache)

    response = post_command("Plan a journey from Berlin to Hamburg", online=True)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_simple"
    assert body["intent"] == "plan_journey"
    assert body["actions"][0]["type"] == "journey_cache_created"
    assert body["actions"][0]["payload"]["source"] == "maps_api"

    search = post_command("Find a fast charger with coffee", online=False)
    assert search.json()["selectedStation"]["id"] == "maps-demo"


def test_offline_reachable_charger_uses_local_cache():
    response = post_command("Find a charger I can reach", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_cache_search"
    assert body["debug"]["cloudUsed"] is False
    assert body["selectedStation"]["reachableWithCurrentRange"] is True


def test_offline_live_availability_falls_back_to_cache():
    response = post_command("Is it available right now?", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "offline_fallback"
    assert body["debug"]["cloudUsed"] is False
    assert body["debug"]["warnings"]


def test_navigate_there_uses_previous_selection():
    first = post_command("Find a fast charger with coffee", online=True)
    selected_id = first.json()["selectedStation"]["id"]

    second = post_command("Navigate there", online=False)
    body = second.json()

    assert second.status_code == 200
    assert body["route"] == "local_simple"
    assert body["actions"][0]["type"] == "start_navigation"
    assert body["selectedStation"]["id"] == selected_id


def test_lights_off_calls_car_api(monkeypatch: pytest.MonkeyPatch):
    from app import main

    calls = []

    def fake_set_lights(enabled):
        calls.append(enabled)
        return {"status": "ok", "vehicle": "test-car:55555"}

    monkeypatch.setattr(main.car_client, "set_lights", fake_set_lights)

    response = post_command("Turn the lights off", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_simple"
    assert body["intent"] == "lights_off"
    assert body["spokenResponse"] == "Turning the lights off."
    assert body["actions"][0]["type"] == "vehicle_lights_off"
    assert body["actions"][0]["payload"]["carApi"]["status"] == "ok"
    assert calls == [False]


def test_lights_on_reports_car_api_unavailable(monkeypatch: pytest.MonkeyPatch):
    from app import main

    def fake_set_lights(enabled):
        raise RuntimeError("offline")

    monkeypatch.setattr(main.car_client, "set_lights", fake_set_lights)

    response = post_command("Switch the headlights on", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_simple"
    assert body["intent"] == "lights_on"
    assert "could not reach the car API" in body["spokenResponse"]
    assert body["actions"][0]["type"] == "vehicle_lights_on"
    assert body["debug"]["warnings"]


def test_vehicle_demo_sequence_calls_car_api(monkeypatch: pytest.MonkeyPatch):
    from app import main

    calls = []

    def fake_run_demo_sequence():
        calls.append("demo")
        return {
            "status": "ok",
            "vehicle": "test-car:55555",
            "steps": [
                {
                    "name": "takeover",
                    "signal": "Vehicle.RequestTakeOver",
                    "value": "[1, 120]",
                    "status": "ok",
                }
            ],
        }

    monkeypatch.setattr(main.car_client, "run_demo_sequence", fake_run_demo_sequence)

    response = post_command("Run the car demo sequence", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["route"] == "local_simple"
    assert body["intent"] == "vehicle_demo_sequence"
    assert body["spokenResponse"] == "Running the Mini Demo Car sequence now."
    assert body["actions"][0]["type"] == "vehicle_demo_sequence"
    assert body["actions"][0]["payload"]["carApi"]["status"] == "ok"
    assert calls == ["demo"]


def test_vehicle_demo_sequence_reports_partial_steps(monkeypatch: pytest.MonkeyPatch):
    from app import main

    def fake_run_demo_sequence():
        return {
            "status": "partial",
            "vehicle": "test-car:55555",
            "steps": [
                {
                    "name": "start_engine",
                    "signal": "Vehicle.Powertrain.StartStop.StartControl",
                    "value": "[1, 120]",
                    "status": "skipped",
                    "detail": "unsupported",
                }
            ],
        }

    monkeypatch.setattr(main.car_client, "run_demo_sequence", fake_run_demo_sequence)

    response = post_command("Show the car demo", online=False)
    body = response.json()

    assert response.status_code == 200
    assert body["intent"] == "vehicle_demo_sequence"
    assert "some vehicle signals were skipped" in body["spokenResponse"]
    assert body["debug"]["warnings"]
