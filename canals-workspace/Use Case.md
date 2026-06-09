# Use Case — Highway Journey

## Scenario

Driver travels between cities (e.g. France → Germany) on a highway.

## Flow

```mermaid
flowchart LR
    Start(["🚗 Journey Start"]) -->|online| Fetch["Fetch Route POIs<br>(Open Maps)"]
    Fetch --> Cache[("MongoDB Cache")]

    Cache --> Drive["Driving"]
    Drive --> Query["Voice Query"]

    Query --> Check{Connected?}
    Check -- Yes --> CloudLLM["Cloud LLM<br>+ Live Data"]
    Check -- No --> LocalLLM["Local LLM<br>+ Cache"]

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
| "Book a hotel" | ☁️ needs cloud |
| Heart rate alert → suggest hospital | ✅ cached locations |

## Cached POI Categories

- Gas stations
- EV charging stations
- Hotels / places to sleep
- Workshops / car garages
- Hospitals / emergency services
- Local points of interest

## Links

- [[Challenge]]
- [[Problem]]
- [[Tech Stack]]
