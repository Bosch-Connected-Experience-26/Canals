# Use Case — Highway Journey

## Scenario

Driver travels between cities (e.g. France → Germany) on a highway.

## Flow

```mermaid
flowchart LR
    Start(["🚗 Journey Start"]) -->|online| Route["OSM Routing<br>(OSRM)"]
    Route -->|GPS path| Fetch["Fetch POIs along route<br>OpenChargeMap + OSM"]
    Fetch --> Cache[("Route Cache<br>MongoDB local")]

    Cache --> Drive["Driving"]
    Drive --> Query["Voice Query"]

    Query --> Check{Connected?}
    Check -- Yes --> CloudLLM["Cloud LLM Agent<br>AWS Bedrock · GPT-OSS"]
    Check -- No --> LocalLLM["Local LLM<br>Ollama · Gemma 4"]

    CloudLLM --> Answer["🔊 Answer"]
    LocalLLM --> Answer
    Answer --> Drive
```

## Queries the Assistant Handles

| Query | Offline? |
|-------|----------|
| "Where's the nearest gas station?" | ✅ |
| "Find an EV charger nearby" | ✅ |
| "I need a place to sleep" | ✅ |
| "Find a workshop / garage" | ✅ |
| "Nearest hospital" | ✅ |
| "I need water / food nearby" | ☁️ online only |
| "Book a hotel" | ☁️ online only |
| Heart rate alert → suggest hospital | ✅ cached locations |

## Cached POI Categories

- Gas stations
- EV charging stations (via OpenChargeMap)
- Hotels / places to sleep
- Workshops / car garages
- Hospitals / emergency services
- Local points of interest

## Links

- [[Challenge]]
- [[Problem]]
- [[Tech Stack]]
- [[Cache Requirements]]
