workspace "Hybrid Vehicle Voice Assistant" "BCX26 — Voice Assistant for Vehicle Control" {

    model {
        driver = person "Driver" "Interacts with the vehicle via voice while driving."

        # ── Vehicle (Edge) ──────────────────────────────────────────────────
        vehicleSystem = softwareSystem "Vehicle (Local)" "Hybrid edge voice assistant running in-vehicle." {
            voiceInput = container "Voice Input" "Captures and interprets driver speech intent." "Picovoice Rhino"
            localLLM   = container "Local LLM" "Processes intents and answers queries offline." "Ollama · Gemma 4 (NVIDIA Jetson)"
            orchestrator = container "Orchestration API" "Central backend service that coordinates routing, cache lookup, cloud calls, vehicle state, and navigation actions." "Python + FastAPI"
            routeCache = container "Route Cache" "Stores pre-fetched POIs for the current journey." "MongoDB (mongodb-atlas-local)" {
                tags "Database" "MongoDB"
            }
            tts        = container "Text To Speech" "Converts assistant response to audio." "On-device TTS"
            vehicleAPI = container "Vehicle Control API" "Controls vehicle functions (lights, climate)." "KUKSA / Vehicle API"
        }

        # ── AWS ─────────────────────────────────────────────────────────────
        awsSystem = softwareSystem "AWS" "Cloud AI services, available when connected." {
            cloudLLM = container "Cloud LLM Agent" "Orchestrates cloud queries and enriches responses." "AWS Lambda / Agent" {
                tags "AWS"
            }
            bedrock  = container "AWS Bedrock" "Hosts and runs the GPT-OSS model." "AWS Bedrock · GPT-OSS" {
                tags "AWS"
            }
        }

        # ── Open Services (OSM space) ────────────────────────────────────────
        osmSystem = softwareSystem "Open Services" "Open routing and EV charging data." {
            osmRouting = container "OSM Routing" "Generates road-accurate GPS paths between two points." "OSRM / OpenStreetMap"
            ocmAPI     = container "OpenChargeMap API" "Provides EV charging station locations and live availability." "OpenChargeMap REST API"
        }

        # ── MongoDB Atlas (Canals space) ─────────────────────────────────────
        mongoSystem = softwareSystem "MongoDB (Canals)" "Managed cloud database with full POI dataset and vector search." {
            atlasDB = container "MongoDB Atlas" "Full global POI dataset with vector search." "MongoDB Atlas" {
                tags "Database" "MongoDB"
            }
        }

        # ── Relationships ────────────────────────────────────────────────────

        # Driver ↔ Vehicle
        driver     -> voiceInput "Speaks query"
        tts        -> driver     "Speaks response"

        # Voice pipeline
        voiceInput -> localLLM  "Transcribed intent"
        localLLM   -> orchestrator "Router decision + command context"
        orchestrator -> localLLM "Local answer request when needed"
        orchestrator -> tts "Response text"
        localLLM   -> vehicleAPI "Vehicle commands (lights, climate)"
        orchestrator -> vehicleAPI "Navigation / vehicle actions"

        # Offline path
        orchestrator -> routeCache "Query cached EV stations (offline)"

        # Online path: Vehicle → AWS
        orchestrator -> cloudLLM "Forward live/current-data query (when connected)"
        cloudLLM -> bedrock  "Invoke model"

        # AWS → Open Services
        cloudLLM -> osmRouting "Get GPS route path"
        cloudLLM -> ocmAPI     "Fetch EV charging data"

        # AWS → MongoDB
        cloudLLM -> atlasDB "Semantic + geo query"
        cloudLLM -> orchestrator "Live availability / pricing result"

        # Cache population at journey start
        osmRouting -> routeCache "Store route waypoints"
        ocmAPI     -> routeCache "Store EV stations along route"
        atlasDB    -> routeCache "Store enriched POI data"
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

        dynamic vehicleSystem "OfflineFlow" "Driver query answered from local cache" {
            driver     -> voiceInput "Where is the nearest EV charger?"
            voiceInput -> localLLM   "Intent: find_ev_charger"
            localLLM   -> orchestrator "local_cache_search decision"
            orchestrator -> routeCache "Nearby EV stations (offline)"
            routeCache -> orchestrator "Station list with positions"
            orchestrator -> tts        "EV station in 2.3 km"
            tts        -> driver     "EV station in 2.3 km, turn left"
            autolayout lr
            title "Offline Flow — EV Query from Cache"
        }

        dynamic vehicleSystem "OnlineFlow" "Driver query enriched by cloud" {
            driver     -> voiceInput "Find me water and a charger"
            voiceInput -> localLLM   "Intent: find_ev_charger + shop"
            localLLM   -> orchestrator "cloud_required decision"
            orchestrator -> cloudLLM   "Query (connected)"
            cloudLLM   -> bedrock    "Invoke model"
            cloudLLM   -> ocmAPI     "Live charger availability"
            cloudLLM   -> atlasDB    "Vector search: EV + shop nearby"
            cloudLLM   -> orchestrator "Rich result"
            orchestrator -> tts        "4 chargers free, shop 200m"
            tts        -> driver     "4 of 6 chargers free, shop 200m ahead"
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
            relationship "Relationship" {
                dashed false
            }
        }
    }
}
