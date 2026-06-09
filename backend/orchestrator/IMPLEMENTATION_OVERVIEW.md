# EV Voice Orchestrator Implementation Overview

## What This Implements

This PR adds a backend orchestration service for the EV charging voice assistant.

The orchestrator is the central API between:

- the voice/UI layer
- the small local model/router
- MongoDB route cache
- AWS/cloud services
- vehicle state
- navigation actions

The main goal is to keep the assistant useful while driving, even when the network is weak or offline.

## Why We Need It

The challenge idea is local-first voice control.

That means the car should not call the cloud just because internet exists. The small local model is always first. It decides whether a request can be handled locally, from cached EV charger data, or whether it truly needs live cloud data.

This makes the demo stronger because it shows:

- offline behavior
- cache-aware routing
- live-data fallback
- a clean API for frontend/mobile teammates
- a clear path to MongoDB and AWS integration

## Main API Endpoints

### `POST /journey/start`

Starts a journey and creates or loads the charger cache.

In the demo, the cache is seeded from local mock EV station data. When MongoDB is running, the journey cache is stored there.

Example:

```json
{
  "journeyId": "trip_001"
}
```

### `POST /command`

Handles a voice command.

It receives:

- transcript
- network state
- vehicle state
- journey ID

Then it:

- asks the local router what to do
- searches MongoDB/local cache if possible
- calls cloud only for live/current data
- ranks charging stations
- returns spoken text, UI payload, debug info, and navigation actions

Example:

```json
{
  "journeyId": "trip_001",
  "transcript": "Find me a 150 kilowatt charger with coffee",
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

Expected behavior:

```json
{
  "route": "local_cache_search",
  "intent": "find_charger",
  "debug": {
    "cloudUsed": false,
    "routeReason": "The request can be answered from cached charging station data."
  }
}
```

Even though the car is online, this stays local because cached route charger data is enough.

### `GET /journey/{journey_id}/cache`

Returns cached charging stations for demo/debug UI.

### `GET /health`

Reports service status and active backends.

Example:

```json
{
  "status": "ok",
  "service": "canals-orchestrator",
  "version": "0.1.0",
  "cacheBackend": "mongodb",
  "cloudBackend": "mock"
}
```

## Routing Behavior

The local router returns one of these labels:

| Route | Meaning |
| --- | --- |
| `local_simple` | Simple local command, such as "Navigate there" |
| `local_cache_search` | Search cached EV stations locally |
| `cloud_required` | Needs live/current data and internet is available |
| `cloud_optional` | Reserved for future cloud-enhanced but not required answers |
| `offline_fallback` | Needs live data, but offline, so use cache with warning |
| `clarify` | User request is too vague |
| `unsupported` | Outside current scope |

## Example Demo Scenarios

### 1. Fast charger with coffee

User says:

```text
Find a fast charger with coffee
```

Result:

```json
{
  "route": "local_cache_search",
  "cloudUsed": false
}
```

Why:

The answer can be found in the local journey cache.

### 2. Live availability while online

User says:

```text
Check live availability
```

Result:

```json
{
  "route": "cloud_required",
  "cloudUsed": true
}
```

Why:

The user explicitly asked for current/live data, so the orchestrator uses the cloud path when internet is available.

### 3. Live availability while offline

User says:

```text
Is it available right now?
```

Network:

```json
{
  "online": false
}
```

Result:

```json
{
  "route": "offline_fallback",
  "cloudUsed": false
}
```

Why:

Live data is impossible while offline, so the assistant answers from cached availability and warns that the data may be stale.

### 4. Navigate there

User says:

```text
Navigate there
```

Result:

```json
{
  "route": "local_simple",
  "actions": [
    {
      "type": "start_navigation"
    }
  ]
}
```

Why:

The orchestrator remembers the previously selected station for that journey and starts navigation locally.

## Station Ranking

The ranking logic filters and scores stations using:

- matching connector, for example `CCS`
- reachability with current range
- requested minimum charging speed
- reliability
- cached availability
- charging speed
- distance and detour
- requested amenities, for example coffee
- price

This means a station is not chosen just because it is closest. It must also be useful and reachable.

## MongoDB Integration

MongoDB is used as the route cache backend.

When the car starts a journey, the orchestrator creates or loads a cache document for that journey.

Default Docker Compose settings:

```text
mongodb://root:root@mongodb:27017/?authSource=admin
```

If MongoDB is unavailable, the service falls back to memory so the demo still works.

## AWS Integration

The cloud path is AWS-ready.

By default, it uses a deterministic mock so the demo does not require AWS credentials.

To enable AWS Bedrock:

```text
AWS_BEDROCK_ENABLED=true
AWS_REGION=eu-central-1
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

This gives us a clean swap point for live availability, live pricing, traffic, or more complex cloud reasoning.

## How To Run

From the repo root:

```bash
docker compose up --build orchestrator
```

Services:

- Maps API: `http://localhost:8000`
- Orchestrator: `http://localhost:8001`
- MongoDB: `localhost:27017`

For local Python development:

```bash
cd backend/orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Short Summary

This implementation gives the team a working orchestration backend for the BCX26 demo.

It proves the core concept:

> The local model decides first. Cached EV charger data is used whenever possible. Cloud is only used when the user explicitly needs live/current information.
