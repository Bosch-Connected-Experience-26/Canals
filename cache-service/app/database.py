from pymongo import MongoClient, GEOSPHERE
from pymongo.collection import Collection

from app.config import MONGODB_URI, DB_NAME, COLLECTION, CLOUD_MONGODB_URI

client: MongoClient   = None
pois: Collection      = None
journeys: Collection  = None

cloud_client: MongoClient  = None
cloud_pois: Collection     = None
cloud_journeys: Collection = None


def connect() -> None:
    global client, pois, journeys, cloud_client, cloud_pois, cloud_journeys

    client   = MongoClient(MONGODB_URI)
    pois     = client[DB_NAME][COLLECTION]
    journeys = client[DB_NAME]["journeys"]
    pois.create_index([("location", GEOSPHERE)])
    pois.create_index([("journey_id", 1)])
    pois.create_index([("source_id", 1), ("poi_type", 1)], unique=True, sparse=True)
    journeys.create_index([("journey_id", 1)], unique=True)

    if CLOUD_MONGODB_URI:
        cloud_client   = MongoClient(CLOUD_MONGODB_URI)
        cloud_pois     = cloud_client[DB_NAME][COLLECTION]
        cloud_journeys = cloud_client[DB_NAME]["journeys"]
        cloud_pois.create_index([("location", GEOSPHERE)])
        cloud_pois.create_index([("journey_id", 1)])
        cloud_pois.create_index([("source_id", 1), ("poi_type", 1)], unique=True, sparse=True)
        cloud_journeys.create_index([("journey_id", 1)], unique=True)
