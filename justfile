structurizr:
    docker run -it --rm \
        -p 8080:8080 \
        -v {{justfile_directory()}}/structurizr:/usr/local/structurizr \
        structurizr/structurizr local


cache-service:
    docker compose up -d --build cache-service

maps-api:
    docker compose up -d maps-api

test:
    docker compose up -d mongodb maps-api cache-service
    docker compose --profile test run --rm e2e

car-api:
    docker compose up -d --build car-api

car-mock:
    docker compose up bosch-car-mock

db:
    docker compose up -d

db-stop:
    docker compose down

# Cache Frankfurt → Berlin route (EV stations along the A9/A2 corridor)
demo-cache:
    curl -X POST http://localhost:8002/journey \
        -H 'Content-Type: application/json' \
        -d '{"start": "Frankfurt", "end": "Berlin", "journey_id": "demo-frankfurt-berlin", "radius_km": 10}'

# Find nearest EV station from Leipzig (midpoint on the Frankfurt–Berlin route)
demo-nearest:
    curl "http://localhost:8002/nearest?lat=51.3397&lng=12.3731&poi_type=ev_charging"

orchestrator:
    docker compose up --build orchestrator

api:
    cd backend/orchestrator && uvicorn app.main:app --reload --port 8000
