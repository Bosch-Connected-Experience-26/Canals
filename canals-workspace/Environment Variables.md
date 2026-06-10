# Environment Variables

All secrets and local overrides go in `.env` at the repo root. The file is gitignored — never commit it.

## Template

Copy this and fill in the blanks:

```env
# --- OpenChargeMap ---
OCM_API_KEY=

# --- OpenAI Whisper STT (or local faster-whisper, see STT_BASE_URL below) ---
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
# Default: mock (Docker internal).
VEHICLE_URL=bosch-car-mock:55555
# Override for real car:
#VEHICLE_URL=192.168.56.6:55555
VEHICLE_CLIENT_ID=120

# --- Ollama (local LLM router) ---
# Container is profile-gated: docker compose --profile ollama up -d ollama
# (or `just ollama-pull` to start it and pull OLLAMA_MODEL).
# If unreachable, orchestrator falls back to the deterministic rule router.
USE_OLLAMA_ROUTER=true
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=gemma4:e4b

# --- Local STT (faster-whisper via speaches) ---
# Container is profile-gated: docker compose --profile stt up -d speaches
# (or `just speaches`). Leave STT_BASE_URL empty to use OpenAI Whisper
# instead (requires OPENAI_API_KEY) — there is no automatic fallback.
STT_BASE_URL=http://speaches:8000/v1
STT_MODEL=Systran/faster-whisper-small

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
| `OPENAI_API_KEY` | Yes for voice | orchestrator | Used by `/transcribe`. Any value works when `STT_BASE_URL` is set to a local server |
| `STT_BASE_URL` | No | orchestrator | OpenAI-compatible STT endpoint, e.g. `http://speaches:8000/v1`. Empty = OpenAI Whisper. No fallback if unreachable — `/transcribe` returns 500 |
| `STT_MODEL` | No | orchestrator | Default `whisper-1`. For speaches: `Systran/faster-whisper-small` — must be downloaded first via `POST http://localhost:8004/v1/models/<model_id>` |
| `PUBLIC_API_BASE` | No | ui | Browser-visible orchestrator URL; default `http://localhost:8001` |
| `MONGODB_URI` | Yes | cache-service, orchestrator | Local Docker URI, auto-overridden in containers |
| `MONGODB_DATABASE` | Yes | cache-service | Default: `route_cache` |
| `MONGODB_COLLECTION` | Yes | cache-service | Default: `pois` |
| `mongo_db_connection` | No | cache-service | Cloud Atlas URI — enables dual-write if set |
| `VEHICLE_URL` | No | car-api | Format `host:port`. Defaults to `bosch-car-mock:55555` if unset, but `.env` value takes precedence |
| `VEHICLE_CLIENT_ID` | No | car-api | Client ID sent with KUKSA commands (default `120`) |
| `USE_OLLAMA_ROUTER` | No | orchestrator | `true` to route intents via local Ollama. Falls back to the rule router if Ollama is unreachable |
| `OLLAMA_BASE_URL` | No | orchestrator | Only used when `USE_OLLAMA_ROUTER=true` |
| `OLLAMA_MODEL` | No | orchestrator | Default `llama3.2:3b` — must be pulled first (`just ollama-pull`) |
| `AWS_REGION` | No | orchestrator | Default `eu-central-1` |
| `AWS_BEDROCK_ENABLED` | No | orchestrator | `true` to enable Bedrock calls |

## Optional Profiles

`ollama` and `speaches` are gated behind Docker Compose profiles — `docker compose up -d` won't start them even if `USE_OLLAMA_ROUTER`/`STT_BASE_URL` point at them.

| Service | Start with | Notes |
|---------|-----------|-------|
| `ollama` | `just ollama-pull` (starts + pulls `OLLAMA_MODEL`) or `docker compose --profile ollama up -d ollama` | Pulling `gemma4:e4b` downloads ~9.6GB |
| `speaches` | `just speaches` or `docker compose --profile stt up -d speaches` | Then download the model: `curl -X POST http://localhost:8004/v1/models/Systran/faster-whisper-small` |

## How Docker compose handles `.env`

Services that declare `env_file: .env` load all vars from the file, but `environment:` blocks in `docker-compose.yml` **take precedence**. Key overrides:

| Service | Override | Reason |
|---------|----------|--------|
| `orchestrator` | `MONGODB_URI` → `mongodb:27017` | container can't reach `localhost` |
| `cache-service` | `MONGODB_URI` → `mongodb:27017` | same |
| `maps-api` | `OCM_API_KEY` → `${OCM_API_KEY:-}` | passes through from `.env` |
| `ui` | `PUBLIC_API_BASE` → `http://localhost:8001` | browser calls host-exposed orchestrator |

`car-api`'s `VEHICLE_URL` uses `${VEHICLE_URL:-bosch-car-mock:55555}` — `.env` value passes through if set, defaults to the mock otherwise. So `.env` values for `MONGODB_URI` are only used when running services **directly on the host** (e.g. `uvicorn` in dev), not inside Docker — but `VEHICLE_URL` from `.env` is respected in both.

## Links

- [[OCM API Key]]
- [[Car Vehicle]]
- [[Car Mock]]
