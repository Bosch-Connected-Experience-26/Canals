workspace "Hybrid Vehicle Voice Assistant" "BCX26 — Voice Assistant for Vehicle Control" {

    model {
        driver    = person "Driver" "Interacts with the vehicle via voice while driving."
        developer = person "Developer" "Runs e2e tests and monitors the system." {
            tags "Developer"
        }

        # ── Vehicle (Edge) ──────────────────────────────────────────────────
        vehicleSystem = softwareSystem "Vehicle (Local)" "Hybrid edge voice assistant running in-vehicle." {
            voiceInput   = container "Voice Input" "Captures and interprets driver speech intent." "Picovoice Rhino"
            localLLM     = container "Local LLM" "Processes intents and answers queries offline." "Ollama · Gemma 4 (NVIDIA Jetson)"
            orchestrator = container "Orchestration API" "Central backend service that coordinates routing, cache lookup, cloud calls, vehicle state, and navigation actions." "Python · FastAPI" {
                tags "API"
            }
            routeCache   = container "Route Cache" "Stores pre-fetched POIs for the current journey. Named volumes: db, configdb, mongot. 2dsphere + journey_id indexes." "MongoDB (mongodb-atlas-local · Docker)" {
                tags "Database" "MongoDB"
            }
            tts          = container "Text To Speech" "Converts assistant response to audio." "On-device TTS"
            vehicleAPI   = container "Vehicle Control API" "Controls vehicle functions (lights, climate)." "KUKSA / Vehicle API"
        }

        # ── AWS ─────────────────────────────────────────────────────────────
        awsSystem = softwareSystem "AWS" "Cloud AI services, available when connected." {
            cloudLLM = container "Cloud LLM Agent" "Orchestrates cloud queries and enriches responses." "AWS Lambda / Agent" {
                tags "AWS"
            }
            bedrock = container "AWS Bedrock" "Hosts and runs the GPT-OSS model." "AWS Bedrock · GPT-OSS" {
                tags "AWS"
            }
        }

        # ── Open Services ────────────────────────────────────────────────────
        osmSystem = softwareSystem "Open Services" "Open routing and EV charging data sources." {
            osmRouting = container "OSM Routing" "Geocoding and road-accurate GPS paths via Nominatim + OSRM." "OSRM · OpenStreetMap · Nominatim"
            ocmAPI     = container "OpenChargeMap API" "EV charging station locations and live availability." "OpenChargeMap REST API"
        }

        # ── MongoDB (Canals) ─────────────────────────────────────────────────
        mongoSystem = softwareSystem "MongoDB (Canals)" "Managed cloud database with full POI dataset and vector search." {
            atlasDB = container "MongoDB Atlas" "Full global POI dataset with vector search." "MongoDB Atlas" {
                tags "Database" "MongoDB"
            }
        }

        # ── Canals API ───────────────────────────────────────────────────────
        canalsAPI = softwareSystem "Canals API" "Our backend services: Maps API proxy, cache builder, car control API, and e2e tests." {
            mapsAPI = container "Maps API" "REST proxy for geocoding, routing and EV data. Swagger UI at /docs." "Python · FastAPI · Docker" {
                tags "API"
            }
            cacheService = container "Cache Service" "Fetches POIs along a route and stores them in local MongoDB. Swagger UI at /docs." "Python · FastAPI · Docker" {
                tags "API"
            }
            carAPI = container "Car API" "REST API for vehicle control commands (lights, etc.). Swagger UI at /docs." "Python · FastAPI · Docker" {
                tags "API"
            }
            boschCarMock = container "KUKSA Databroker Mock" "Mock KUKSA databroker for local development. Logs all VSS signal writes, no hardware required." "ghcr.io/eclipse-kuksa/kuksa-databroker · Docker" {
                tags "Mock"
            }
            e2eTests = container "E2E Tests" "12 automated end-to-end tests: 5 Maps API (geocode, route, EV stations) + 7 Cache Service (journey CRUD, nearby offline). Frankfurt → Munich." "Python · pytest · httpx · Docker" {
                tags "Tests"
            }
        }

        # ── Relationships ────────────────────────────────────────────────────

        # Driver ↔ Vehicle
        driver       -> voiceInput   "Speaks query"
        tts          -> driver       "Speaks response"

        # Voice pipeline
        voiceInput   -> localLLM     "Transcribed intent"
        localLLM     -> orchestrator "Router decision + command context"
        orchestrator -> localLLM     "Local answer request when needed"
        orchestrator -> tts          "Response text"
        localLLM     -> vehicleAPI   "Vehicle commands (lights, climate)"
        orchestrator -> vehicleAPI   "Navigation / vehicle actions"

        # Offline path
        orchestrator -> routeCache   "Query cached POIs (offline)"

        # Online path: Orchestrator → AWS
        orchestrator -> cloudLLM     "Forward live query (when connected)"
        cloudLLM     -> bedrock      "Invoke model"
        cloudLLM     -> osmRouting   "Get GPS route path"
        cloudLLM     -> ocmAPI       "Fetch live EV data"
        cloudLLM     -> atlasDB      "Semantic + geo query"
        cloudLLM     -> orchestrator "Live availability / pricing result"

        # Cache population at journey start via Cache Service
        localLLM     -> cacheService "POST /journey at journey start"
        cacheService -> mapsAPI      "GET /route/cities + /ev-stations"
        mapsAPI      -> osmRouting   "Geocode city names + get GPS route (OSRM)"
        mapsAPI      -> ocmAPI       "Fetch EV stations along route"
        cacheService -> routeCache   "Upsert POIs (2dsphere indexed)"
        atlasDB      -> routeCache   "Store enriched POI data"

        # Offline nearby query
        orchestrator -> cacheService "GET /nearby?lat=&lng= (offline)"

        # Car API → vehicle (production path uses real KUKSA broker)
        developer    -> carAPI       "POST /lights/on|off (Swagger UI)"
        carAPI       -> vehicleAPI   "KUKSA gRPC set_current_values"

        # Car API → mock (local dev)
        carAPI       -> boschCarMock "KUKSA gRPC set_current_values (mock)"

        # E2E Tests
        developer    -> e2eTests     "Runs tests"
        e2eTests     -> mapsAPI      "HTTP requests (geocode, route, EV stations)"
        e2eTests     -> cacheService "HTTP requests (POST /journey, GET /journey/*, GET /nearby)"
    }

    views {
        systemLandscape "Landscape" {
            include *
            autolayout lr
            title "System Landscape — Hybrid Vehicle Voice Assistant"
        }

        container vehicleSystem "VehicleContainers" {
            include *
            autolayout tb
            title "Vehicle (Local) — Containers"
        }

        container awsSystem "AWSContainers" {
            include *
            autolayout tb
            title "AWS — Containers"
        }

        container osmSystem "OSMContainers" {
            include *
            autolayout tb
            title "Open Services — Containers"
        }

        container mongoSystem "MongoContainers" {
            include *
            autolayout tb
            title "MongoDB (Canals) — Containers"
        }

        container canalsAPI "CanalsAPIContainers" {
            include *
            autolayout tb
            title "Canals API — Containers"
        }

        dynamic canalsAPI "LocalMockRun" "Developer controls vehicle via mock KUKSA broker" {
            developer    -> carAPI        "POST /lights/off"
            carAPI       -> boschCarMock  "gRPC: Vehicle.Body.Lights.ExteriorLightControl"
            autolayout lr
            title "Local Mock Run — Light Control via KUKSA Mock"
        }

        dynamic canalsAPI "E2EFlow" "E2E test: Frankfurt → Munich route" {
            developer    -> e2eTests    "just test"
            e2eTests     -> mapsAPI     "GET /geocode?location=Frankfurt"
            e2eTests     -> mapsAPI     "GET /geocode?location=Munich"
            e2eTests     -> mapsAPI     "GET /route/cities?start=Frankfurt&end=Munich"
            mapsAPI      -> osmRouting  "Geocode city names + OSRM GPS path"
            e2eTests     -> mapsAPI     "GET /route/ev-stations"
            mapsAPI      -> ocmAPI      "EV stations along waypoints"
            e2eTests     -> cacheService "POST /journey (Frankfurt → Munich, radius 10 km)"
            cacheService -> mapsAPI     "GET /route/cities + GET /route/ev-stations"
            cacheService -> routeCache  "Upsert POIs (2dsphere indexed)"
            e2eTests     -> cacheService "GET /journey/{id}/pois"
            e2eTests     -> cacheService "GET /nearby?lat=50.11&lng=8.68&radius_m=15000"
            autolayout lr
            title "E2E Flow — Frankfurt → Munich"
        }

        dynamic vehicleSystem "OfflineFlow" "Driver query answered from local cache" {
            driver       -> voiceInput   "Where is the nearest EV charger?"
            voiceInput   -> localLLM     "Intent: find_ev_charger"
            localLLM     -> orchestrator "local_cache_search decision"
            orchestrator -> routeCache   "Nearby EV stations (offline)"
            routeCache   -> orchestrator "Station list with positions"
            orchestrator -> tts          "EV station in 2.3 km"
            tts          -> driver       "EV station in 2.3 km, turn left"
            autolayout lr
            title "Offline Flow — EV Query from Cache"
        }

        dynamic vehicleSystem "OnlineFlow" "Driver query enriched by cloud" {
            driver       -> voiceInput   "Find me water and a charger"
            voiceInput   -> localLLM     "Intent: find_ev_charger + shop"
            localLLM     -> orchestrator "cloud_required decision"
            orchestrator -> cloudLLM     "Query (connected)"
            cloudLLM     -> bedrock      "Invoke model"
            cloudLLM     -> ocmAPI       "Live charger availability"
            cloudLLM     -> atlasDB      "Vector search: EV + shop nearby"
            cloudLLM     -> orchestrator "Rich result"
            orchestrator -> tts          "4 chargers free, shop 200m"
            tts          -> driver       "4 of 6 chargers free, shop 200m ahead"
            autolayout lr
            title "Online Flow — Enriched Query via Cloud"
        }

        styles {
            element "Person" {
                shape Person
                background #08427B
                color #ffffff
                fontSize 22
            }
            element "Developer" {
                shape Person
                background #555555
                color #ffffff
                fontSize 22
            }
            element "Software System" {
                background #1168BD
                color #ffffff
            }
            element "Container" {
                background #438DD5
                color #ffffff
            }
            element "Database" {
                shape Cylinder
                background #438DD5
                color #ffffff
            }
            element "AWS" {
                background #FF9900
                color #000000
                icon "icons/bedrock.png"
            }
            element "MongoDB" {
                background #47A248
                color #ffffff
                icon "icons/mongodb.png"
            }
            element "API" {
                shape Component
                background #2D6A4F
                color #ffffff
            }
            element "Mock" {
                shape Component
                background #8B4513
                color #ffffff
            }
            element "Tests" {
                shape Component
                background #6B6B6B
                color #ffffff
            }
            relationship "Relationship" {
                dashed false
            }
        }
    }
}
