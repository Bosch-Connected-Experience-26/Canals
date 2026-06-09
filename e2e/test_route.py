#!/usr/bin/env python3
"""
End-to-end test: Frankfurt → Munich
  1. Geocode both cities
  2. Fetch 10 route waypoints
  3. Fetch EV stations along the route
"""

import sys
import httpx

import os
BASE = os.getenv("MAPS_API_URL", "http://maps-api:8000")


def check(label: str, resp: httpx.Response) -> dict:
    if resp.status_code != 200:
        print(f"FAIL  {label} — HTTP {resp.status_code}: {resp.text}")
        sys.exit(1)
    data = resp.json()
    print(f"OK    {label}")
    return data


def main():
    client = httpx.Client(timeout=30)

    print("\n── 1. Geocode ──────────────────────────────────────────")
    frankfurt = check("Geocode Frankfurt", client.get(f"{BASE}/geocode", params={"location": "Frankfurt"}))
    munich    = check("Geocode Munich",    client.get(f"{BASE}/geocode", params={"location": "Munich"}))
    print(f"      Frankfurt → {frankfurt['lat']:.5f}, {frankfurt['lng']:.5f}")
    print(f"      Munich    → {munich['lat']:.5f}, {munich['lng']:.5f}")

    print("\n── 2. Route waypoints ──────────────────────────────────")
    route = check(
        "Route Frankfurt → Munich",
        client.get(f"{BASE}/route/cities", params={"start": "Frankfurt", "end": "Munich"}),
    )
    print(f"      Distance : {route['distance_km']} km")
    print(f"      Duration : {route['duration_min']:.0f} min")
    print(f"      Waypoints: {len(route['waypoints'])}")
    for i, wp in enumerate(route["waypoints"]):
        print(f"        [{i+1:2d}] {wp['lat']:.5f}, {wp['lng']:.5f}")

    print("\n── 3. EV stations along route ──────────────────────────")
    ev = check(
        "EV stations Frankfurt → Munich",
        client.get(
            f"{BASE}/route/ev-stations",
            params={
                "start_lat": frankfurt["lat"],
                "start_lng": frankfurt["lng"],
                "end_lat":   munich["lat"],
                "end_lng":   munich["lng"],
                "radius_km": 10,
            },
        ),
    )
    print(f"      Found {len(ev)} unique EV stations\n")
    for s in ev[:10]:
        print(f"        [{s['id']}] {s['name']} ({s['lat']:.5f}, {s['lng']:.5f}) — {s['connections']} connector(s)")
    if len(ev) > 10:
        print(f"        ... and {len(ev) - 10} more")

    print("\n── PASS ─────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
