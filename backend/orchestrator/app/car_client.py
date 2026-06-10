from __future__ import annotations

import httpx

from .config import Settings


class CarApiClient:
    def __init__(self, settings: Settings) -> None:
        self.base_url = settings.car_api_base_url.rstrip("/")
        self.timeout = settings.car_api_timeout_seconds

    def set_lights(self, enabled: bool) -> dict:
        path = "on" if enabled else "off"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(f"{self.base_url}/lights/{path}")
            response.raise_for_status()
            return response.json()

    def run_demo_sequence(self) -> dict:
        with httpx.Client(timeout=max(self.timeout, 10)) as client:
            response = client.post(f"{self.base_url}/demo/sequence")
            response.raise_for_status()
            return response.json()
