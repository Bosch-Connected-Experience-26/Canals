# AGENTS.md

Guidance for AI agents working in this repository.

## Project Context

This repo is for the BCX26 "Voice Assistant for Vehicle Control" challenge.

The project is a hybrid, local-first in-vehicle voice assistant. The current demo focus is an offline-aware EV charging assistant:

- At journey start, EV charger and route data is fetched/cached.
- During the journey, voice commands are routed through a local-first decision layer.
- Cached data should be used whenever it can answer the request.
- Cloud/AWS should only be used when the user explicitly needs live/current data or complex reasoning.
- Offline fallback behavior must remain demonstrable.

Do not turn this into a cloud-first assistant. The local router/model is always first.

## Important Architecture Rule

Routing policy:

1. Local router/model is always called first.
2. Simple requests stay local.
3. Requests answerable from cached EV station data stay local, even when internet is available.
4. Explicit live/current data requests use cloud only when online.
5. Explicit live/current data requests while offline use cached data with a freshness warning.
6. Cloud is for live availability, live pricing, traffic, external web data, or reasoning the local model cannot confidently handle.

Required route labels:

- `local_simple`
- `local_cache_search`
- `cloud_required`
- `cloud_optional`
- `offline_fallback`
- `clarify`
- `unsupported`

## Repo Map

- `backend/orchestrator/`
  - FastAPI orchestration backend.
  - Central API between voice/UI, local router, MongoDB route cache, AWS/cloud path, vehicle state, and navigation actions.
  - Main app: `backend/orchestrator/app/main.py`
  - Pydantic contracts: `backend/orchestrator/app/models.py`
  - Local routing policy: `backend/orchestrator/app/router.py`
  - Station ranking: `backend/orchestrator/app/ranking.py`
  - MongoDB-backed journey cache with memory fallback: `backend/orchestrator/app/cache.py`
  - AWS Bedrock-ready cloud gateway with mock fallback: `backend/orchestrator/app/cloud.py`
  - Settings/env defaults: `backend/orchestrator/app/config.py`
  - Mock EV station data: `backend/orchestrator/app/data/mock_stations.json`
  - Tests: `backend/orchestrator/tests/`
  - Human explanation artefact: `backend/orchestrator/IMPLEMENTATION_OVERVIEW.md`

- `maps-api/`
  - Maps/route API service added on `main`.
  - Runs on host port `8000` through Docker Compose.

- `Docker/`
  - Dockerfiles for MongoDB, maps API, and orchestrator.

- `docker-compose.yml`
  - Runs MongoDB, maps API, and orchestrator.
  - Host ports:
    - maps API: `localhost:8000`
    - orchestrator: `localhost:8001`
    - MongoDB: `localhost:27017`

- `structurizr/workspace.dsl`
  - Architecture diagram source.
  - The older root `workspace.dsl` was moved to this folder on `main`; do not reintroduce the root file.

- `canals-workspace/`
  - Challenge notes, use case notes, tech stack notes, and cache requirements.

- `kuksa/`
  - Vehicle API/KUKSA reference material.

## Common Commands

From the repo root:

```bash
docker compose config
docker compose up --build orchestrator
just db
just maps-api
just orchestrator
```

Run the orchestrator locally:

```bash
cd backend/orchestrator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Run orchestrator tests:

```bash
cd backend/orchestrator
python -m pytest tests
```

Compile-check Python without writing bytecode outside the workspace:

```bash
python3 -X pycache_prefix=/tmp/canals_pycache -m compileall backend/orchestrator/app
```

## Orchestrator API

Core endpoints:

- `GET /health`
- `POST /journey/start`
- `POST /command`
- `GET /journey/{journey_id}/cache`

The `/command` response should include:

- `route`
- `spokenResponse`
- `intent`
- `selectedStation`
- `alternatives`
- `actions`
- `debug`

Debug info should keep showing:

- whether cloud was used
- why the route was chosen
- cache freshness
- router decision

## Demo Scenarios To Preserve

Do not break these:

1. Start journey online and cache stations.
2. "Find a fast charger with coffee" returns `local_cache_search`, even if online.
3. "Check live availability" returns `cloud_required` if online.
4. Offline + "Find a charger I can reach" returns `local_cache_search`.
5. Offline + "Is it available right now?" returns `offline_fallback` with a cache freshness warning.
6. "Navigate there" returns `local_simple` and starts navigation to the previous selected station.

## Cache And Cloud Expectations

MongoDB is the intended route cache backend. The orchestrator should keep a memory fallback because demos and tests must work without Docker or MongoDB running.

AWS Bedrock is the intended cloud LLM/service path. Keep `AWS_BEDROCK_ENABLED=false` by default so local tests and demos do not require credentials. When AWS is unavailable, fall back to deterministic mock behavior.

## Coding Guidance

- Prefer small, practical changes. This is a hackathon repo.
- Keep API contracts stable for frontend/mobile teammates.
- Use Pydantic models for request/response contracts.
- Keep mock data and mock cloud paths swappable.
- Do not use cloud just because `network.online` is true.
- Do not remove offline fallback behavior.
- Do not overwrite teammate notes, diagrams, or files from `main`.
- If `main` changes, rebase carefully and preserve:
  - `maps-api`
  - `structurizr/workspace.dsl`
  - Docker Compose services
  - orchestrator port `8001` in Compose unless the team intentionally changes ports

## Git Notes

The current PR branch for the orchestrator work is:

```text
codex/ev-orchestrator
```

The repo uses the personal SSH host alias:

```text
github-personal:Bosch-Connected-Experience-26/Canals.git
```

If pushes fail due to auth, confirm SSH with:

```bash
ssh -T github-personal
```

Expected successful account:

```text
Hi WeebPapi! You've successfully authenticated, but GitHub does not provide shell access.
```

## Validation Before Pushing

At minimum, run:

```bash
docker compose config
cd backend/orchestrator && python -m pytest tests
```

If dependencies are not installed, create a local venv in `backend/orchestrator/.venv`. The `.venv` directory is ignored and should not be committed.
