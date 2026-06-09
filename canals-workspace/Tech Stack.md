# Tech Stack

## Vehicle (Local / Edge)

| Component | Technology |
|-----------|-----------|
| Hardware | NVIDIA Jetson |
| Speech-to-Intent | Picovoice Rhino (on-device) |
| Local LLM | Ollama · Gemma 4 (offline) |
| Route Cache | MongoDB (mongodb-atlas-local, Docker) |
| Text-to-Speech | On-device TTS |
| Vehicle Control | KUKSA / Vehicle API |

## AWS

| Component | Technology |
|-----------|-----------|
| Cloud LLM Agent | AWS Lambda / Agent |
| Model | AWS Bedrock · GPT-OSS |

## Open Services

| Component | Technology |
|-----------|-----------|
| Routing | OSRM / OpenStreetMap |
| EV Data | OpenChargeMap REST API |

## MongoDB (Canals)

| Component | Technology |
|-----------|-----------|
| Cloud Database | MongoDB Atlas |
| Vector Search | Atlas Vector Search |

## Data Flow

```mermaid
flowchart TD
    Voice["🎙️ Voice Input<br>Picovoice Rhino"] --> LLM["Local LLM<br>Ollama · Gemma 4"]

    LLM --> Check{Connected?}

    Check -- Yes --> CloudLLM["Cloud LLM Agent<br>(AWS Lambda)"]
    CloudLLM --> Bedrock["AWS Bedrock<br>GPT-OSS"]
    CloudLLM --> OSM["OSRM<br>OpenStreetMap"]
    CloudLLM --> OCM["OpenChargeMap API"]
    CloudLLM --> Atlas[("MongoDB Atlas")]

    Check -- No --> Cache[("Route Cache<br>MongoDB local")]

    Cache --> TTS["🔊 Text-to-Speech"]
    CloudLLM --> TTS

    TTS --> Driver["👤 Driver"]
```

## Links

- [[Challenge]]
- [[Problem]]
- [[Use Case]]
- [[Cache Requirements]]
