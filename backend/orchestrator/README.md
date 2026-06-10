# Canals EV Voice Orchestrator

Hackathon-friendly FastAPI service for offline-aware EV charging voice control.

The local router is always called first. It handles simple vehicle questions and cached station search locally, routes explicit live/current-data requests to the cloud only when online, and falls back to cached data with a freshness warning when offline.

The route cache is backed by MongoDB when available. For local resilience, the service falls back to an in-memory cache if MongoDB or `pymongo` is unavailable. Cloud/live enrichment is AWS Bedrock-ready and uses a deterministic mock unless `AWS_BEDROCK_ENABLED=true`.

## Run

With Docker Compose from the repo root:

```bash
docker compose up --build orchestrator
```

This starts:

- `mongodb` on `localhost:27017`
- `maps-api` on `localhost:8000`
- `orchestrator` on `localhost:8001`

For local Python development:

```bash
cd backend/orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

- API docs: `http://localhost:8000/docs` when running with Uvicorn directly, or `http://localhost:8001/docs` through Docker Compose
- Health: `http://localhost:8000/health` when running with Uvicorn directly, or `http://localhost:8001/health` through Docker Compose

## Configuration

Defaults match the repo Docker Compose setup.

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://root:root@localhost:27017/?authSource=admin` | MongoDB route-cache connection |
| `MONGODB_DATABASE` | `canals` | Mongo database name |
| `MONGODB_COLLECTION` | `journey_caches` | Journey cache collection |
| `OPENAI_API_KEY` | unset | Auth for `/transcribe` (OpenAI Whisper, or any key when using a local STT_BASE_URL) |
| `STT_BASE_URL` | unset | OpenAI-compatible STT endpoint for `/transcribe`, e.g. `http://speaches:8000/v1` for local faster-whisper. Empty = OpenAI Whisper |
| `STT_MODEL` | `whisper-1` | Model id passed to `/transcribe`, e.g. `Systran/faster-whisper-small` for speaches |
| `MAPS_API_BASE_URL` | `http://localhost:8000` | Maps/route service used by journey planning |
| `CAR_API_BASE_URL` | `http://localhost:8003` | Car API service for lights commands |
| `AWS_BEDROCK_ENABLED` | `false` | Enable AWS Bedrock for cloud/live enrichment |
| `AWS_REGION` | `eu-central-1` | AWS region |
| `AWS_BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model ID |

`GET /health` reports the active cache and cloud backend, for example:

```json
{
  "status": "ok",
  "service": "canals-orchestrator",
  "version": "0.1.0",
  "cacheBackend": "mongodb",
  "cloudBackend": "mock"
}
```

## Endpoints

### `GET /health`

Returns service status.

### `POST /journey/start`

Creates or loads a journey cache in MongoDB from local mock station data. This remains useful as a fallback and for tests.

```json
{
  "journeyId": "trip_001",
  "origin": {"lat": 52.52, "lng": 13.405, "label": "Berlin"},
  "destination": {"lat": 48.137, "lng": 11.575, "label": "Munich"}
}
```

### `GET /journey/{journey_id}/cache`

Returns cached stations and metadata for demo/debug UI.

### `POST /command`

Receives a voice transcript and state, asks the local router what to do, executes local/cloud/fallback behavior, ranks stations when relevant, and returns voice/UI/navigation payloads.

For the primary UI demo, send a transcript like `"Plan a journey from Berlin to Hamburg"`. The orchestrator classifies it as `plan_journey`, calls maps-api for geocoding, route waypoints, and OpenChargeMap stations, then replaces the journey cache with route-specific station data.

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

Response shape:

```json
{
  "route": "local_cache_search",
  "spokenResponse": "I recommend Canals FastCharge Coffee Mitte...",
  "intent": "find_charger",
  "selectedStation": {},
  "alternatives": [],
  "actions": [
    {
      "type": "start_navigation",
      "stationId": "berlin_fast_coffee_01",
      "label": "Navigate to Canals FastCharge Coffee Mitte",
      "payload": {"lat": 52.535, "lng": 13.42}
    }
  ],
  "debug": {
    "cloudUsed": false,
    "routeReason": "The request can be answered from cached charging station data.",
    "cacheAgeMinutes": 0,
    "cacheGeneratedAt": "2026-06-09T12:00:00Z",
    "cacheStationCount": 6,
    "warnings": [],
    "routerDecision": {}
  }
}
```

## Routing Labels

- `local_simple`: simple local action or answer, such as vehicle battery status or "Navigate there".
- `local_cache_search`: station search answerable from cached route data.
- `cloud_required`: explicit live/current data request while online.
- `cloud_optional`: reserved for future cases where cloud could improve the answer but is not required.
- `offline_fallback`: live/current data requested while offline; answer from cache with warning.
- `clarify`: insufficient context.
- `unsupported`: outside the supported charging/navigation scope.

## Demo Scenarios

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Plan a journey from Berlin to Hamburg",
    "network":{"online":true,"latencyMs":80},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

Local cached search, even while online:

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Find a fast charger with coffee",
    "network":{"online":true,"latencyMs":80},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

Cloud required for live availability while online:

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Check live availability",
    "network":{"online":true,"latencyMs":80},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

Offline cache search:

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Find a charger I can reach",
    "network":{"online":false},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

Offline fallback for live availability:

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Is it available right now?",
    "network":{"online":false},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

Navigate to the previous selected station:

```bash
curl -s -X POST http://localhost:8000/command \
  -H 'Content-Type: application/json' \
  -d '{
    "journeyId":"trip_001",
    "transcript":"Navigate there",
    "network":{"online":false},
    "vehicle":{"batteryPercent":34,"rangeKm":145,"lat":52.52,"lng":13.405,"connector":"CCS"}
  }'
```

## Swap Points

- Replace `app/router.py::decide_route` with the small local LLM call.
- Extend `app/cloud.py::CloudGateway` for AWS Bedrock, live availability, pricing, and traffic services.
- Extend `app/cache.py::JourneyCacheStore` with richer MongoDB indexes or MongoDB Atlas sync.
- Replace `app/data/mock_stations.json` with route-prefetched charger data.
