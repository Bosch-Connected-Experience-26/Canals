# Environment Variables

All secrets and local overrides go in `.env` at the repo root. The file is gitignored — never commit it.

## Template

Copy this and fill in the blanks:

```env
# --- OpenChargeMap ---
OCM_API_KEY=

# --- OpenAI Whisper STT ---
OPENAI_API_KEY=

# --- UI ---
PUBLIC_API_BASE=http://localhost:8001

# --- MongoDB (local Docker) ---
MONGODB_URI=mongodb://root:root@localhost:27017/?authSource=admin
MONGODB_DATABASE=route_cache
MONGODB_COLLECTION=pois

# --- MongoDB Atlas (cloud, optional) ---
# Leave empty to skip cloud writes in cache-service
mongo_db_connection=

# --- Vehicle ---
# Default: mock (Docker internal). Override for real car:
# VEHICLE_URL=192.168.56.6:55555
VEHICLE_URL=bosch-car-mock:55555
VEHICLE_CLIENT_ID=120

# --- Ollama (optional, enable with --profile ollama) ---
USE_OLLAMA_ROUTER=false
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b

# --- AWS Bedrock (optional) ---
AWS_REGION=eu-central-1
AWS_BEDROCK_ENABLED=false
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
```

## Variable Reference

| Variable | Required | Used by | Notes |
|----------|----------|---------|-------|
| `OCM_API_KEY` | Yes | maps-api | OpenChargeMap API key — see [[OCM API Key]] |
| `OPENAI_API_KEY` | Yes for voice | orchestrator | Used by `/transcribe` for Whisper STT |
| `PUBLIC_API_BASE` | No | ui | Browser-visible orchestrator URL; default `http://localhost:8001` |
| `MONGODB_URI` | Yes | cache-service, orchestrator | Local Docker URI, auto-overridden in containers |
| `MONGODB_DATABASE` | Yes | cache-service | Default: `route_cache` |
| `MONGODB_COLLECTION` | Yes | cache-service | Default: `pois` |
| `mongo_db_connection` | No | cache-service | Cloud Atlas URI — enables dual-write if set |
| `VEHICLE_URL` | No | car-api | Format `host:port`. Docker overrides to `bosch-car-mock:55555` |
| `VEHICLE_CLIENT_ID` | No | car-api | Client ID sent with KUKSA commands (default `120`) |
| `USE_OLLAMA_ROUTER` | No | orchestrator | `true` to route via local Ollama instead of Bedrock |
| `OLLAMA_BASE_URL` | No | orchestrator | Only used when `USE_OLLAMA_ROUTER=true` |
| `OLLAMA_MODEL` | No | orchestrator | Default `llama3.2:3b` |
| `AWS_REGION` | No | orchestrator | Default `eu-central-1` |
| `AWS_BEDROCK_ENABLED` | No | orchestrator | `true` to enable Bedrock calls |

## How Docker compose handles `.env`

Services that declare `env_file: .env` load all vars from the file, but `environment:` blocks in `docker-compose.yml` **take precedence**. Key overrides:

| Service | Override | Reason |
|---------|----------|--------|
| `orchestrator` | `MONGODB_URI` → `mongodb:27017` | container can't reach `localhost` |
| `cache-service` | `MONGODB_URI` → `mongodb:27017` | same |
| `car-api` | `VEHICLE_URL` → `bosch-car-mock:55555` | always mock inside Docker |
| `maps-api` | `OCM_API_KEY` → `${OCM_API_KEY:-}` | passes through from `.env` |
| `ui` | `PUBLIC_API_BASE` → `http://localhost:8001` | browser calls host-exposed orchestrator |

So `.env` values for `MONGODB_URI` and `VEHICLE_URL` are only used when running services **directly on the host** (e.g. `uvicorn` in dev), not inside Docker.

## Links

- [[OCM API Key]]
- [[Car Vehicle]]
- [[Car Mock]]
