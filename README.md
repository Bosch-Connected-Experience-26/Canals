<div align="center">

#  Canals

### *The voice that drives with you — even when the cloud doesn't.*

**Hybrid AI-powered in-vehicle voice assistant for EV charging control.**  
Local-first. Cloud-optional. Always responsive.

[![BCX26](https://img.shields.io/badge/Bosch%20Connected%20Experience-2026-red?style=for-the-badge)](https://bcw.bosch-connected-world.com/)
[![AWS](https://img.shields.io/badge/Powered%20by-AWS%20Bedrock-FF9900?style=for-the-badge&logo=amazon-aws)](https://aws.amazon.com/bedrock/)
[![MongoDB](https://img.shields.io/badge/Cache-MongoDB-47A248?style=for-the-badge&logo=mongodb)](https://www.mongodb.com/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Astro](https://img.shields.io/badge/UI-Astro-FF5D01?style=for-the-badge&logo=astro)](https://astro.build/)

---

🔗 **[Live Demo →](https://your-production-url-here.com)** &nbsp;|&nbsp; 📖 **[API Docs →](http://localhost:8001/docs)** &nbsp;|&nbsp; 🎥 **[Pitch Deck →](#)**

---

</div>

## The Problem

Today's in-vehicle voice assistants are **entirely cloud-dependent**. Dead zones, highway tunnels, weak LTE — and your assistant goes silent. For an EV driver asking *"Where is the next charging port for my electric car?"* this isn't just inconvenient. It's a broken experience at exactly the wrong moment.

| Pain Point | Status Quo | Canals |
|---|---|---|
| **Offline reliability** | ❌ Full failure | ✅ Local-first always responds |
| **Latency** | ❌ 800ms+ round-trip | ✅ <50ms local path |
| **EV-specific context** | ❌ Generic assistants | ✅ Range-aware, connector-aware |
| **Live charger data** | ❌ Stale or none | ✅ Cloud-enriched when online |
| **Map visualisation** | ❌ Text only | ✅ Interactive charger map |

---

##  The Canals Approach 🧠

```
"Show me fast chargers with coffee near me"
         │
         ▼
  ┌─────────────┐     always runs first, <50ms
  │ Local Router│─────────────────────────────────► Local cache hit? ──► Spoken response
  └─────────────┘                                                         + Map pins
         │ needs live data AND online
         ▼
  ┌─────────────┐
  │ AWS Bedrock │─────────────────────────────────► Enriched live data ──► Response
  └─────────────┘
         │ needs live data AND offline
         ▼
  ┌─────────────┐
  │ Cache + warn│─────────────────────────────────► Stale-aware answer
  └─────────────┘
```

The **local model decides first, every time**. Cloud is only called when the user explicitly needs current data *and* is online. This mirrors how production automotive software must behave under ISO 26262 functional safety principles.

---

##  System Architecture 🗺️

```mermaid
graph TB
    subgraph Vehicle["🚗 In-Vehicle Layer"]
        Mic["🎤 Microphone"]
        Whisper["Whisper STT<br/>(OpenAI API)"]
        TTS["🔊 Web Speech TTS"]
        UI["Astro UI<br/>+ Leaflet Map"]
        Mic --> Whisper
        Whisper --> UI
        UI --> TTS
    end

    subgraph Orchestrator["⚙️ Orchestrator (FastAPI :8001)"]
        Transcribe["/transcribe"]
        Command["/command"]
        Router["Local AI Router<br/>(intent detection)"]
        Ranker["Station Ranker<br/>(score + filter)"]
        Transcribe --> Command
        Command --> Router
        Router --> Ranker
    end

    subgraph Cache["💾 Route Cache Layer"]
        MongoDB["MongoDB<br/>(journey cache)"]
        Fallback["In-Memory<br/>(offline fallback)"]
        MongoDB -.->|unavailable| Fallback
    end

    subgraph Cloud["☁️ Cloud Services"]
        Bedrock["AWS Bedrock<br/>Claude Haiku"]
        MapsAPI["Maps API<br/>(:8000)"]
        CarAPI["Car API<br/>(KUKSA / Bosch)"]
    end

    UI -->|"POST audio"| Transcribe
    UI -->|"POST transcript + vehicle state"| Command
    Router -->|"local_cache_search"| MongoDB
    Router -->|"cloud_required + online"| Bedrock
    Ranker --> UI
    MapsAPI -->|"prefetch route chargers"| MongoDB
    CarAPI -->|"vehicle state"| Command
```

---

##  Data Model 🏗️

```mermaid
erDiagram
    JOURNEY {
        string journeyId PK
        datetime generatedAt
        int stationCount
        string source
    }

    STATION {
        string id PK
        string name
        float lat
        float lng
        float distanceKm
        float detourKm
        int maxKw
        float reliability
        bool reachableWithCurrentRange
        float estimatedArrivalBatteryPercent
        float score
        float priceEurPerKwh
    }

    AVAILABILITY {
        string status
        int availableStalls
        int totalStalls
        string source
    }

    COMMAND_REQUEST {
        string journeyId FK
        string transcript
        bool networkOnline
        float batteryPercent
        float rangeKm
        float vehicleLat
        float vehicleLng
        string connector
    }

    COMMAND_RESPONSE {
        string route
        string spokenResponse
        string intent
        bool cloudUsed
        string routeReason
        int cacheAgeMinutes
    }

    ACTION {
        string type
        string stationId FK
        string label
        json payload
    }

    JOURNEY ||--o{ STATION : "caches"
    STATION ||--|| AVAILABILITY : "has"
    COMMAND_REQUEST ||--|| JOURNEY : "references"
    COMMAND_REQUEST ||--|| COMMAND_RESPONSE : "produces"
    COMMAND_RESPONSE ||--o{ ACTION : "triggers"
    COMMAND_RESPONSE ||--o| STATION : "selectedStation"
```

---

##  Voice Command Flow 🔀

```mermaid
sequenceDiagram
    actor Driver
    participant UI as Astro UI
    participant API as Orchestrator
    participant Router as Local Router
    participant Cache as MongoDB Cache
    participant Cloud as AWS Bedrock

    Driver->>UI: Press mic, speak
    UI->>API: POST /transcribe (audio blob)
    API-->>UI: { text: "Show me nearby chargers on the map" }
    UI->>API: POST /command (transcript + vehicle state)
    API->>Router: decide intent
    Router-->>API: local_cache_search + show_map intent
    API->>Cache: rank stations by range, kW, amenities
    Cache-->>API: ranked stations [ ]
    API-->>UI: spokenResponse + actions[show_map] + selectedStation + alternatives
    UI-->>Driver: 🔊 "I recommend Canals FastCharge Coffee Mitte..."
    UI-->>Driver: 🗺️ Leaflet map with green + blue pins
```

---

##  System Boundaries 🗂️

```mermaid
graph LR
    subgraph Edge["Edge (Always Available)"]
        A["Local AI Router"]
        B["MongoDB Cache<br/>prefetched on journey start"]
        C["In-memory fallback"]
        D["Astro UI + Leaflet"]
        E["Web Speech API TTS"]
    end

    subgraph Hybrid["Hybrid (Online-enhanced)"]
        F["Whisper STT<br/>OpenAI API"]
        G["AWS Bedrock<br/>Live availability / pricing"]
        H["Maps API<br/>Route-prefetch"]
    end

    subgraph External["External Integrations"]
        I["KUKSA Vehicle API"]
        J["Bosch Car API"]
        K["Charging network APIs"]
    end

    Edge -->|"triggers when online"| Hybrid
    Hybrid -->|"enriches"| Edge
    External -->|"vehicle state + lights"| Edge
```

**What always works offline:**
- Battery / range queries
- Station search from journey cache
- Navigate to previously selected station
- Map display of cached stations
- Lights on/off via Car API (direct CAN)

**What requires connectivity:**
- Live charger availability
- Real-time pricing
- Fresh route-based charger prefetch

---

## 🔧 Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Voice input** | OpenAI Whisper | Best-in-class multilingual STT |
| **Voice output** | Web Speech API | Zero-latency, no cloud needed |
| **Local router** | Python + custom NLP | <50ms, no model download |
| **Cloud AI** | AWS Bedrock (Claude Haiku) | Cost-efficient, low latency |
| **Backend** | FastAPI + Python | Auto-docs, async, typed |
| **Route cache** | MongoDB | Offline-resilient document store |
| **Maps** | Leaflet.js + OpenStreetMap | MIT licensed, no API key |
| **Frontend** | Astro.js | Zero JS by default, fast |
| **Vehicle API** | KUKSA Data Broker | Open standard for in-vehicle signals |
| **Infrastructure** | Docker Compose | One-command local stack |

---

## 🚘 Real-World Car Implementation

### How Canals Maps to Production Automotive Architecture

```mermaid
graph TB
    subgraph HPC["High-Performance Computer (HPC)"]
        VoiceZone["Voice Domain Controller"]
        MiddlewareZone["AUTOSAR Adaptive<br/>Middleware"]
        ConnectivityZone["5G/V2X Modem"]
    end

    subgraph OurStack["Canals → Production Mapping"]
        Whisper2["Whisper → On-device STT model<br/>(e.g. Whisper.cpp on ARM)"]
        Router2["Local Router → Tiny LLM<br/>(Qwen-0.5B, <500MB RAM)"]
        Cache2["MongoDB → SQLite/LevelDB<br/>(embedded, no daemon)"]
        API2["FastAPI → SOME/IP service<br/>(AUTOSAR AA)"]
        UI2["Astro UI → HMI render engine<br/>(Qt / Android Auto)"]
    end

    HPC -->|"maps to"| OurStack
```

### Production Benefits

| Metric | Cloud-only | Canals Local-First |
|---|---|---|
| **Response latency** | 800–2000ms | **40–80ms** |
| **Offline uptime** | 0% | **~95% of commands** |
| **Data cost/vehicle/month** | ~2GB | **~200MB** (cloud top-up only) |
| **GDPR risk** | High (voice in cloud) | **Low** (audio stays on-device) |
| **Functional safety** | Degraded mode only | **Full fallback design** |

### Cost Model at Scale (Fleet of 100k Vehicles)

```
Cloud-only architecture
  └─ 100k vehicles × 200 commands/day × 365 days
  └─ ~730M API calls/year
  └─ ~€2.2M/year in LLM API costs alone

Canals local-first
  └─ 95% resolved locally → 36.5M cloud calls/year
  └─ ~€110k/year (-95% cloud cost)
  └─ One-time: ~€15/vehicle embedded compute upgrade
  └─ Break-even: < 3 months at fleet scale
```

---

## 📊 Analytics & Testing

**Key metrics:** local resolution rate (target >90%), P95 local latency (<80ms), offline fallback triggers (<5%), STT word error rate (<8%).

**At Bosch scale:** start with pytest unit coverage on the router, replay real EV driver intents against the orchestrator, then a 50-vehicle opt-in pilot with A/B against cloud-only — measuring task completion rate offline as the primary KPI.

---

## 🔮 What's Next

- **Proactive range alerts** — warn the driver before they ask
- **Multi-stop planning** — "plan Berlin → Munich with charges"
- **On-device Whisper.cpp** — eliminate the STT API call entirely
- **V2X slot reservation** — charger broadcasts directly to the car
- **Android Auto / CarPlay HMI** — native head-unit integration
- **AUTOSAR Adaptive port** — production-ready SOME/IP service

---

## ❓ FAQ

**What does "Canals" stand for?**
> Two things at once. It's the first letter of every team member's name — **C**hristian, **A**lex, **N**ico, **A**bdulla, **L**i, **S**ofiia — and it doubles as **C**onnected **A**utomotive **N**atural-language **A**ssistant for **L**ocal **S**earch. It's also a nod to waterways: networks that route traffic efficiently even when the main road is blocked, just like our local-first routing.

**Why is the UI in a web browser and not an actual car screen?**
> This is a hackathon prototype. The architecture is identical to what would run in a real HMI — the Astro UI maps 1:1 to a Qt or Android Auto render layer, and the FastAPI backend would become an AUTOSAR Adaptive SOME/IP service. The browser is just our fastest path to a working demo in 48 hours.

**Why OpenStreetMap instead of Google Maps or HERE?**
> OSM + Leaflet.js is MIT licensed and completely free — no API key, no usage cap, no legal review needed for a Bosch hackathon demo. In production, Bosch's existing HERE Maps contract would slot straight in.

**Does it actually work offline?**
> Yes — if the journey cache has been pre-loaded (via `/journey/start`), charger search, range queries, and map display all work with zero network. The STT step (Whisper) still needs a connection in this prototype; production would swap in Whisper.cpp running on-device.

**What's the dummy vehicle state for the demo?**
> Central Berlin (52.52°N, 13.405°E), 80% battery, 200 km range, CCS connector. Swap in real KUKSA signals by pointing `car-api/` at your KUKSA Data Broker instance.

**Can Canals run on a Raspberry Pi / embedded board?**
> The orchestrator (FastAPI + local router) runs comfortably on 512 MB RAM. The heaviest dependency is MongoDB — swap for SQLite and it fits on a Raspberry Pi 4 with room to spare.

---

## 👥 Team

| Name | Role | GitHub |
|---|---|---|
| **Abdulla** | Web UI · Map integration · Backend routing | [@abdalla980](https://github.com/abdalla980) |
| **Alex** | Frontend · Backend | [@TBD](#) |
| **Christian** | Backend · Software Architecture · ML | [@TBD](#) |
| **Li** | Product Design · UX · Product Journey | [@TBD](#) |
| **Nico** | Automation · Business · Product | [@TBD](#) |
| **Sofiia** | TBD | [@TBD](#) |

> **Challenge:** Voice Assistant for Vehicle Control — Future Mobility (Automotive)
> **Event:** [Bosch Connected Experience 2026](https://bcw.bosch-connected-world.com/) · BCX26

---

## 🚀 Quick Start

### One-command stack (Docker)

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Voice UI | http://localhost:4321 |
| Orchestrator API | http://localhost:8001 |
| API Docs (Swagger) | http://localhost:8001/docs |
| Maps API | http://localhost:8000 |
| MongoDB | localhost:27017 |

### Local development

```bash
# Backend
cd backend/orchestrator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd ui
npm install && npm run dev
```

Set environment variables for full cloud features:

```bash
OPENAI_API_KEY=sk-...          # Whisper STT
AWS_BEDROCK_ENABLED=true       # Live availability via Claude Haiku
AWS_REGION=eu-central-1
MONGODB_URI=mongodb://...      # Optional — falls back to memory
```

---

## 📁 Project Structure

```
canals/
├── ui/                         # Astro.js voice UI + Leaflet map
├── backend/
│   └── orchestrator/           # FastAPI — command routing + cache
├── maps-api/                   # Route-based charger prefetch
├── car-api/                    # KUKSA / Bosch vehicle signals
├── cache-service/              # MongoDB journey cache service
├── bedrock/                    # AWS Bedrock integration
├── infrastructure/             # Terraform / deployment
├── e2e/                        # End-to-end test suite
└── docker-compose.yml          # Full local stack
```

---

<div align="center">

Built with ❤️ at **Bosch Connected Experience 2026**

*Bosch · AWS · MongoDB*

</div>
