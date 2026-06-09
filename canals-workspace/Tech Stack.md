# Tech Stack

## Edge (In-Vehicle)

| Component | Technology |
|-----------|-----------|
| Hardware | NVIDIA Jetson |
| Speech-to-Text | Picovoice Rino (on-device) |
| Local LLM | Edge model (offline) |
| Cache | MongoDB |
| Text-to-Speech | On-device TTS |

## Cloud (When Connected)

| Component | Technology |
|-----------|-----------|
| Cloud LLM | AWS Bedrock |
| Maps / POI | Open Maps API |
| Infrastructure | AWS |

## Data Flow

```mermaid
flowchart TD
    Voice["🎙️ Voice Input"] --> STT["Picovoice Rino<br>(Speech-to-Text)"]
    STT --> LLM["Local LLM<br>(NVIDIA Jetson)"]

    LLM --> Check{Connected?}

    Check -- Yes --> CloudLLM["AWS Bedrock<br>(Cloud LLM)"]
    CloudLLM --> Maps["Open Maps API"]
    Maps --> TTS

    Check -- No --> Cache[("MongoDB Cache<br>(Offline POIs)")]
    Cache --> TTS["🔊 Text-to-Speech"]

    CloudLLM --> TTS
    TTS --> Driver["👤 Driver"]
```

## Links

- [[Challenge]]
- [[Problem]]
- [[Use Case]]
