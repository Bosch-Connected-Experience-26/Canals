# Car Mock (KUKSA Databroker)

Local stand-in for the real Bosch car during development. Runs the official Eclipse KUKSA databroker with a custom VSS spec that mirrors the signals the real vehicle exposes.

## Start

```bash
just car-mock
# or
docker compose up bosch-car-mock
```

Logs stream to stdout. Every VSS signal write appears as a log line.

## Image

```
ghcr.io/eclipse-kuksa/kuksa-databroker:main
```

Started with `--insecure --vss /data/vss_bosch.json`. The `--insecure` flag disables TLS — fine for local dev, never in production.

## Custom VSS Spec

`Docker/vss_bosch.json` defines the two signals the Bosch demo car supports:

| VSS Path | Type | Format | Description |
|----------|------|--------|-------------|
| `Vehicle.RequestTakeOver` | actuator (string) | `[priority, client_id]` | Must be sent before any command |
| `Vehicle.Body.Lights.ExteriorLightControl` | actuator (string) | `[on/off, light_id, client_id]` | Controls exterior lights |
| `Vehicle.Powertrain.StartStop.StartControl` | actuator (string) | `[start/stop, client_id]` | Used by the demo sequence |
| `Vehicle.Chassis.Accelerator.PedalPositionControl` | actuator (string) | `[pedal_percent, client_id]` | Used by the demo sequence |

The VSS JSON uses nested `children` format (not the flat VSS 6.0 standard). The databroker assigns internal IDs at startup — signals appear by ID in broker logs, by path in gRPC logs.

## Log Output

```
RUST_LOG=databroker::broker=debug,databroker::grpc::kuksa_val_v2=debug
```

Set in `docker-compose.yml`. A `POST /lights/off` call produces:

```
setting id 6 to EntryUpdate { ... value: String("[1, 120]") }    ← RequestTakeOver
setting id 5 to EntryUpdate { ... value: String("[0, 0, 120]") } ← ExteriorLightControl
```

## Ports

| Host | Container | Protocol |
|------|-----------|----------|
| `55556` | `55555` | gRPC (KUKSA val v2) |

Host port is `55556` because Docker Desktop reserves `55555` internally. Containers connect via `bosch-car-mock:55555` (Docker service name, no port mapping needed).

## Signal Write Sequence

Every command must follow this order:

```
1. set Vehicle.RequestTakeOver  → "[priority, client_id]"
2. set Vehicle.Body.Lights.ExteriorLightControl → "[on/off, light_id, client_id]"
```

The car rejects commands from a client that hasn't taken over first.

## Links

- [[Car API]]
- [[Car Vehicle]]
