from fastapi.testclient import TestClient

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
