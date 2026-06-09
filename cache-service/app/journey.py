import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException

from app import database as db
from app.maps import fetch_waypoints, fetch_ev_stations, build_poi_doc
from app.models import JourneyRequest, JourneyStatus, PoiSummary

router = APIRouter(tags=["Journey"])


@router.post("/journey", response_model=JourneyStatus, summary="Cache all POIs along a route")
async def create_journey_cache(req: JourneyRequest):
    """
    Geocodes start + end, fetches route waypoints, queries EV stations per waypoint,
    and stores all POIs in local MongoDB tagged with a journey_id.
    """
    journey_id = req.journey_id or str(uuid.uuid4())[:8]
    waypoints  = await fetch_waypoints(req.start, req.end)

    seen: set[str] = set()
    stored = 0

    for wp in waypoints:
        stations = await fetch_ev_stations(wp["lat"], wp["lng"], req.radius_km)
        for s in stations:
            key = str(s["id"])
            if key in seen:
                continue
            seen.add(key)
            doc = build_poi_doc(s, journey_id)
            db.pois.update_one(
                {"source_id": doc["source_id"], "poi_type": "ev_charging"},
                {"$set": doc},
                upsert=True,
            )
            stored += 1

    now = datetime.now(timezone.utc).isoformat()
    db.journeys.update_one(
        {"journey_id": journey_id},
        {"$set": {"journey_id": journey_id, "start": req.start, "end": req.end, "created_at": now}},
        upsert=True,
    )
    return JourneyStatus(
        journey_id=journey_id,
        start=req.start,
        end=req.end,
        poi_count=stored,
        status="complete",
        created_at=now,
    )


@router.get("/journey/{journey_id}", response_model=JourneyStatus, summary="Get journey cache status")
def get_journey(journey_id: str):
    """Returns POI count and metadata for a cached journey."""
    meta  = db.journeys.find_one({"journey_id": journey_id}, {"_id": 0})
    count = db.pois.count_documents({"journey_id": journey_id})
    if meta is None and count == 0:
        raise HTTPException(status_code=404, detail="Journey not found")
    return JourneyStatus(
        journey_id=journey_id,
        start=meta.get("start", "") if meta else "",
        end=meta.get("end", "") if meta else "",
        poi_count=count,
        status="complete",
        created_at=meta.get("created_at", "") if meta else "",
    )


@router.get(
    "/journey/{journey_id}/pois",
    response_model=list[PoiSummary],
    summary="List cached POIs for a journey",
)
def list_pois(journey_id: str, poi_type: Optional[str] = None):
    """Returns all cached POIs for a journey, optionally filtered by poi_type."""
    query: dict = {"journey_id": journey_id}
    if poi_type:
        query["poi_type"] = poi_type

    results = []
    for doc in db.pois.find(query, {"_id": 0}):
        coords = doc["location"]["coordinates"]
        results.append(PoiSummary(
            source_id=doc["source_id"],
            poi_type=doc["poi_type"],
            name=doc["name"],
            lat=coords[1],
            lng=coords[0],
            town=doc.get("town"),
            country=doc.get("country"),
            connections=doc.get("connections", 0),
        ))
    return results


@router.delete("/journey/{journey_id}", summary="Delete cached POIs for a journey")
def delete_journey(journey_id: str):
    """Removes all cached POIs and journey metadata for the given journey_id."""
    result = db.pois.delete_many({"journey_id": journey_id})
    db.journeys.delete_one({"journey_id": journey_id})
    return {"journey_id": journey_id, "deleted": result.deleted_count}
