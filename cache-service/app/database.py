from pymongo import MongoClient, GEOSPHERE
from pymongo.collection import Collection

from app.config import MONGODB_URI, DB_NAME, COLLECTION

client: MongoClient   = None
pois: Collection      = None
journeys: Collection  = None


def connect() -> None:
    global client, pois, journeys
    client   = MongoClient(MONGODB_URI)
    pois     = client[DB_NAME][COLLECTION]
    journeys = client[DB_NAME]["journeys"]
    pois.create_index([("location", GEOSPHERE)])
    pois.create_index([("journey_id", 1)])
    pois.create_index([("source_id", 1), ("poi_type", 1)], unique=True, sparse=True)
    journeys.create_index([("journey_id", 1)], unique=True)
