from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_database: str
    mongodb_collection: str
    maps_api_base_url: str
    use_ollama_router: bool
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: float
    stt_base_url: str
    stt_model: str
    car_api_base_url: str
    car_api_timeout_seconds: float
    aws_bedrock_enabled: bool
    aws_region: str
    aws_bedrock_model_id: str


def load_settings() -> Settings:
    return Settings(
        mongodb_uri=os.getenv(
            "MONGODB_URI",
            "mongodb://root:root@localhost:27017/?authSource=admin",
        ),
        mongodb_database=os.getenv("MONGODB_DATABASE", "canals"),
        mongodb_collection=os.getenv("MONGODB_COLLECTION", "journey_caches"),
        maps_api_base_url=os.getenv("MAPS_API_BASE_URL", "http://localhost:8000"),
        use_ollama_router=os.getenv("USE_OLLAMA_ROUTER", "false").lower() == "true",
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        ollama_timeout_seconds=float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "3")),
        stt_base_url=os.getenv("STT_BASE_URL", ""),
        stt_model=os.getenv("STT_MODEL", "whisper-1"),
        car_api_base_url=os.getenv("CAR_API_BASE_URL", "http://localhost:8003"),
        car_api_timeout_seconds=float(os.getenv("CAR_API_TIMEOUT_SECONDS", "3")),
        aws_bedrock_enabled=os.getenv("AWS_BEDROCK_ENABLED", "false").lower() == "true",
        aws_region=os.getenv("AWS_REGION", "eu-central-1"),
        aws_bedrock_model_id=os.getenv(
            "AWS_BEDROCK_MODEL_ID",
            "anthropic.claude-3-haiku-20240307-v1:0",
        ),
    )
