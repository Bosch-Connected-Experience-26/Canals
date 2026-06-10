set dotenv-load := true

structurizr:
<<<<<<< HEAD
    docker run -it --rm \
        -p 8080:8080 \
        -v /c/Users/nicok/code/canals/Canals/structurizr:/usr/local/structurizr \
        structurizr/structurizr local
=======
    docker compose up -d structurizr
>>>>>>> 4811b1f67cca0e555eb728a9313e6a8f50c0e679


cache-service:
    docker compose up -d --build cache-service

ui:
    docker compose up -d --build ui

maps-api:
    docker compose up -d maps-api

test:
    docker compose up -d mongodb maps-api cache-service bosch-car-mock car-api
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

demo-e2e:
    powershell -ExecutionPolicy Bypass -File scripts/demo-e2e.ps1

orchestrator:
    docker compose up --build orchestrator

ollama-pull:
    docker compose up -d ollama
    docker compose exec ollama ollama pull "${OLLAMA_MODEL:-llama3.2:3b}"

speaches:
    docker compose --profile stt up -d speaches

api:
    cd backend/orchestrator && uvicorn app.main:app --reload --port 8000
