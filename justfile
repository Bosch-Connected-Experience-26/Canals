structurizr:
    docker run -it --rm \
        -p 8080:8080 \
        -v {{justfile_directory()}}/structurizr:/usr/local/structurizr \
        structurizr/structurizr local


maps-api:
    docker compose up -d maps-api

db:
    docker compose up -d

db-stop:
    docker compose down
