structurizr:
    docker run -it --rm \
        -p 8080:8080 \
        -v {{justfile_directory()}}:/usr/local/structurizr \
        structurizr/structurizr local


db:
    docker compose up -d

db-stop:
    docker compose down
