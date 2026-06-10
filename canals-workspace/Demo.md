# Demo Flow

This is the hackathon demo path for the UI-backed, local-first EV charging assistant.

## Start The Stack

From the repo root:

```bash
docker compose up -d --build ui
```

Useful URLs:

```text
Voice UI:     http://localhost:4321
Orchestrator: http://localhost:8001/docs
Maps API:     http://localhost:8000/docs
Car API:      http://localhost:8003/docs
```

## UI Demo Flow

1. Keep the UI online.
2. Say or click `Plan a journey from Berlin to Hamburg`.
   - Expected route: `local_simple`
   - Expected action: `journey_cache_created`
   - Expected cache source: `maps_api`
   - Meaning: route waypoints and OpenChargeMap stations are cached in MongoDB.
3. The cached route-charger map appears.
4. Toggle offline.
5. Say `Find a charger I can reach`.
   - Expected route: `local_cache_search`
   - Expected cloud: `false`
   - Meaning: cached route data is enough, so the assistant stays local.
6. Change `Current Location` on the map, then ask again.
   - Expected: the selected station changes based on simulated car location.
   - Meaning: cached stations are ranked against current vehicle state, not a fixed point.
7. Ask `Is it available right now?` while offline.
   - Expected route: `offline_fallback`
   - Meaning: live data is unavailable, so cached data is used with a warning.
8. Say `Navigate there`.
   - Expected route: `local_simple`
   - Expected action: `start_navigation`
9. Say `Turn the lights off` or `Turn the lights on`.
   - Expected route: `local_simple`
   - Expected actions: `vehicle_lights_off`, `vehicle_lights_on`
10. Say `Run the car demo sequence`.
   - Expected route: `local_simple`
   - Expected action: `vehicle_demo_sequence`
   - Meaning: the assistant triggers the KUKSA Mini Demo Car sequence through the Car API.

## Run The Scripted Demo

From PowerShell:

```powershell
.\scripts\demo-e2e.ps1
```

The script sends representative `/command` requests without using the browser UI.

## What The Demo Proves

1. Plan a journey while online and cache route chargers.
2. Ask for a fast charger with coffee.
   - Expected route: `local_cache_search`
   - Expected cloud: `false`
   - Meaning: cached route data is enough, so the assistant stays local even if online.
3. Ask for live availability while online.
   - Expected route: `cloud_required`
   - Expected cloud: `true`
   - Meaning: explicit live/current requests use the cloud path.
4. Ask for live availability while offline.
   - Expected route: `offline_fallback`
   - Expected cloud: `false`
   - Meaning: live data is unavailable, so cached data is used with a warning.
5. Say `Navigate there`.
   - Expected route: `local_simple`
   - Expected action: `start_navigation`
   - Meaning: the assistant remembers the selected station.
6. Say `Turn the lights off` and `Turn the lights on`.
   - Expected route: `local_simple`
   - Expected actions: `vehicle_lights_off`, `vehicle_lights_on`
   - Meaning: voice-style commands can reach the Car API and KUKSA mock path.
7. Say `Run the car demo sequence`.
   - Expected route: `local_simple`
   - Expected action: `vehicle_demo_sequence`
   - Meaning: the orchestrator can trigger a multi-step KUKSA vehicle demo while keeping vehicle control behind the Car API.

## UI Contract

The UI should call:

```text
POST http://localhost:8001/command
```

with:

```json
{
  "journeyId": "demo-trip",
  "transcript": "Find a fast charger with coffee",
  "network": {
    "online": true,
    "latencyMs": 80
  },
  "vehicle": {
    "batteryPercent": 34,
    "rangeKm": 145,
    "lat": 52.52,
    "lng": 13.405,
    "connector": "CCS"
  }
}
```

Display these response fields first:

```text
spokenResponse
route
intent
debug.cloudUsed
selectedStation.name
selectedStation.distanceKm
selectedStation.estimatedArrivalBatteryPercent
actions[0].type
debug.warnings
```

Suggested preset commands:

```text
Plan a journey from Berlin to Hamburg
Find a fast charger with coffee
Check live availability
Is it available right now?
Find a charger I can reach
Navigate there
Turn the lights off
Turn the lights on
Run the car demo sequence
```

The UI also sends the simulated vehicle location from the map controls in `vehicle.lat` and `vehicle.lng`.
