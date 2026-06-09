from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_database: str
    mongodb_collection: str
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
        aws_bedrock_enabled=os.getenv("AWS_BEDROCK_ENABLED", "false").lower() == "true",
        aws_region=os.getenv("AWS_REGION", "eu-central-1"),
        aws_bedrock_model_id=os.getenv(
            "AWS_BEDROCK_MODEL_ID",
            "anthropic.claude-3-haiku-20240307-v1:0",
        ),
    )
