structurizr:
    docker run -it --rm \
        -p 8080:8080 \
        -v {{justfile_directory()}}/structurizr:/usr/local/structurizr \
        structurizr/structurizr local


maps-api:
    docker compose up -d maps-api

test:
    docker compose --profile test run --rm e2e

db:
    docker compose up -d

db-stop:
    docker compose down

orchestrator:
    docker compose up --build orchestrator

api:
    cd backend/orchestrator && uvicorn app.main:app --reload --port 8000
