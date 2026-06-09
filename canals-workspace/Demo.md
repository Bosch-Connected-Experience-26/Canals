# Demo Flow

This is the backend demo path to keep stable before the UI is merged.

## Start The Stack

From the repo root:

```bash
docker compose up --build orchestrator cache-service maps-api mongodb car-api bosch-car-mock
```

Useful URLs:

```text
Orchestrator: http://localhost:8001/docs
Maps API:     http://localhost:8000/docs
Cache API:    http://localhost:8002/docs
Car API:      http://localhost:8003/docs
```

## Run The Scripted Demo

From PowerShell:

```powershell
.\scripts\demo-e2e.ps1
```

The script sends the same `/command` requests the UI should send later.

## What The Demo Proves

1. Start a journey cache.
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
5. Say "Navigate there".
   - Expected route: `local_simple`
   - Expected action: `start_navigation`
   - Meaning: the assistant remembers the selected station.
6. Say "Turn the lights off" and "Turn the lights on".
   - Expected route: `local_simple`
   - Expected actions: `vehicle_lights_off`, `vehicle_lights_on`
   - Meaning: voice-style commands can reach the Car API and KUKSA mock path.
   - Note: "lights off" sends the known-good all-lights-off command, not a single-light-off command.

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
actions[0].type
debug.warnings
```

Suggested preset buttons:

```text
Find a fast charger with coffee
Check live availability
Is it available right now?
Find a charger I can reach
Navigate there
Turn the lights off
Turn the lights on
```
