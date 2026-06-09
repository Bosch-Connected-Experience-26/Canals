workspace "Hybrid Vehicle Voice Assistant" "BCX26 — Voice Assistant for Vehicle Control" {

    model {
        driver = person "Driver" "Interacts with the vehicle via voice while driving."

        vehicleSystem = softwareSystem "Vehicle System" "Hybrid edge/cloud voice assistant running in the vehicle." {

            voiceInput = container "Voice Input" "Captures driver speech." "Picovoice Rino"
            localLLM = container "Local LLM" "Processes intents and answers queries offline." "Edge LLM (NVIDIA Jetson)"
            routeCache = container "Route Cache" "Stores pre-fetched POIs for the current journey." "MongoDB (Docker / mongodb-atlas-local)" {
                tags "Database"
            }
            tts = container "Text To Speech" "Converts assistant response to audio." "On-device TTS"
            vehicleAPI = container "Vehicle Control API" "Controls vehicle functions (lights, climate)." "KUKSA / Vehicle API"
        }

        cloudSystem = softwareSystem "Cloud System" "Online services used when connectivity is available." "External" {
            cloudLLM = container "Cloud LLM" "Enriches responses with live data." "AWS Bedrock"
            atlasDB = container "MongoDB Atlas" "Full global POI dataset with vector search." "MongoDB Atlas" {
                tags "Database"
            }
            externalAPIs = container "External APIs" "Live POI data sources." "OpenChargeMap, OpenStreetMap, Overpass"
        }

        # People → Vehicle
        driver -> voiceInput "Speaks query"
        tts -> driver "Speaks response"

        # Voice pipeline
        voiceInput -> localLLM "Transcribed intent"
        localLLM -> tts "Response text"
        localLLM -> vehicleAPI "Vehicle commands (lights, climate)"

        # Offline path
        localLLM -> routeCache "Query nearby POIs (offline)"

        # Online path
        localLLM -> cloudLLM "Forward query (when connected)"
        cloudLLM -> atlasDB "Semantic + geo query"
        cloudLLM -> externalAPIs "Live data lookup"

        # Cache population at journey start
        externalAPIs -> routeCache "Pre-fetch route POIs at journey start"
        atlasDB -> routeCache "Rich POI data at journey start"
    }

    views {
        systemContext vehicleSystem "SystemContext" {
            include *
            autolayout lr
            title "System Context — Hybrid Vehicle Voice Assistant"
        }

        container vehicleSystem "VehicleContainers" {
            include *
            autolayout tb
            title "Vehicle System — Containers"
        }

        container cloudSystem "CloudContainers" {
            include *
            autolayout tb
            title "Cloud System — Containers"
        }

        dynamic vehicleSystem "OfflineFlow" "Driver query answered from local cache" {
            driver -> voiceInput "Where is the nearest EV charger?"
            voiceInput -> localLLM "Intent: find_ev_charger"
            localLLM -> routeCache "Nearby EV stations (offline)"
            routeCache -> localLLM "Station list with positions"
            localLLM -> tts "EV station in 2.3 km"
            tts -> driver "EV station in 2.3 km, turn left"
            autolayout lr
            title "Offline Flow — EV Query from Cache"
        }

        dynamic vehicleSystem "OnlineFlow" "Driver query enriched by cloud" {
            driver -> voiceInput "Find me water and a charger"
            voiceInput -> localLLM "Intent: find_ev_charger + shop"
            localLLM -> cloudLLM "Query (connected)"
            cloudLLM -> atlasDB "Vector search: EV + shop nearby"
            cloudLLM -> externalAPIs "Live charger availability"
            cloudLLM -> localLLM "Rich result"
            localLLM -> tts "4 chargers free, shop 200m"
            tts -> driver "4 of 6 chargers free, shop 200m ahead"
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
            element "External" {
                background #999999
                color #ffffff
            }
            relationship "Relationship" {
                dashed false
            }
        }
    }
}
