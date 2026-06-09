# OCM API Key (OpenChargeMap)

The maps-api uses [OpenChargeMap](https://openchargemap.org) to fetch EV charging stations along a route. An API key is required — the free tier is sufficient for development and hackathon use.

## Get a Key

1. Go to [https://openchargemap.org/site/developerinfo](https://openchargemap.org/site/developerinfo)
2. Create a free account (email + password)
3. Navigate to **My Profile → API Keys → Register a new application**
4. Fill in app name (e.g. `Canals BCX26`) and description
5. Copy the generated key

## Set the Key

Add to `.env`:

```env
OCM_API_KEY=
```

The maps-api picks it up via `${OCM_API_KEY:-}` in `docker-compose.yml` and reads it in `maps-api/app/config.py`:

```python
OCM_API_KEY = os.getenv("OCM_API_KEY", "")
```

## Usage

The key is sent as a query parameter on every OCM request:

```
GET https://api.openchargemap.io/v3/poi/?output=json&key=<OCM_API_KEY>&latitude=...
```

Without a key, OCM still responds but rate-limits aggressively (~10 req/day). With a free key the limit is generous enough for development.

## Endpoint

`GET /route/ev-stations` in maps-api internally calls OCM with the waypoints sampled along the route. The key is never exposed in any maps-api response.

## Links

- [[Environment Variables]]
