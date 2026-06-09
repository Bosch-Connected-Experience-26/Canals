import os

OSRM_URL      = "https://router.project-osrm.org/route/v1/driving"
OCM_URL       = "https://api.openchargemap.io/v3/poi/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OCM_API_KEY   = os.getenv("OCM_API_KEY", "")
