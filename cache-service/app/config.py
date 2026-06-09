import os

from dotenv import load_dotenv

load_dotenv()

MAPS_API_URL = os.getenv("MAPS_API_URL", "http://maps-api:8000")
MONGODB_URI  = os.getenv("MONGODB_URI", "mongodb://root:root@mongodb:27017/?authSource=admin")
DB_NAME      = os.getenv("MONGODB_DATABASE", "route_cache")
COLLECTION   = os.getenv("MONGODB_COLLECTION", "pois")
