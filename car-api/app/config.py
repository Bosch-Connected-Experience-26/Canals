import os

from dotenv import load_dotenv

load_dotenv()

# VEHICLE_URL format: host:port  (e.g. bosch-car-mock:55555)
_raw = os.getenv("VEHICLE_URL", "localhost:55555")
_parts = _raw.rsplit(":", 1)
VEHICLE_HOST = _parts[0]
VEHICLE_PORT = int(_parts[1]) if len(_parts) == 2 else 55555

