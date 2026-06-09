from typing import Optional

from fastapi import APIRouter, HTTPException

from app import database as db
from app.models import NearestPoi, PoiSummary

router = APIRouter(tags=["Offline"])


@router.get("/nearby", response_model=list[PoiSummary], summary="Find cached POIs near a position")
def nearby(lat: float, lng: float, radius_m: float = 10000, poi_type: Optional[str] = None):
    """
    Geospatial query on local cache — works fully offline.
    Returns POIs within radius_m metres of the given coordinate.
    """
    query: dict = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                "$maxDistance": radius_m,
            }
        }
    }
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


@router.get("/nearest", response_model=NearestPoi, summary="Find the single nearest cached POI")
def nearest(lat: float, lng: float, poi_type: Optional[str] = None):
    """
    Returns the closest cached POI to the given coordinate, with distance in metres.
    Works fully offline via MongoDB $geoNear aggregation.
    """
    geo_near: dict = {
        "near": {"type": "Point", "coordinates": [lng, lat]},
        "distanceField": "distance_m",
        "spherical": True,
    }
    if poi_type:
        geo_near["query"] = {"poi_type": poi_type}

    pipeline = [{"$geoNear": geo_near}, {"$limit": 1}]
    docs = list(db.pois.aggregate(pipeline))
    if not docs:
        raise HTTPException(status_code=404, detail="No cached POIs found")

    doc    = docs[0]
    coords = doc["location"]["coordinates"]
    return NearestPoi(
        source_id=doc["source_id"],
        poi_type=doc["poi_type"],
        name=doc["name"],
        lat=coords[1],
        lng=coords[0],
        town=doc.get("town"),
        country=doc.get("country"),
        connections=doc.get("connections", 0),
        distance_m=round(doc["distance_m"], 1),
    )
