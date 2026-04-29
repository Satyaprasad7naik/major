from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional
from dotenv import load_dotenv
from urllib.parse import quote
import os

# Explicitly load .env file
load_dotenv()

# Default Redis URL (local); overridden by REDIS_URL or built from REDIS_* below
_DEFAULT_REDIS_URL = "hack-deriv-realtime-6ur8gt.serverless.aps1.cache.amazonaws.com:6379"


class Settings(BaseSettings):
    PROJECT_NAME: str = "NL2SQL Pipeline"
    API_V1_STR: str = "/api/v1"
    
    # LLM Settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-3-flash-preview"
    OPENAI_API_KEY: Optional[str] = None
    # stage-specific models
    INTENT_MODEL: str = os.getenv("INTENT_MODEL", "gemini-2.5-flash-lite")
    SQL_MODEL: str = os.getenv("SQL_MODEL", "gemini-2.5-flash-lite")
    CLARIFICATION_MODEL: str = os.getenv("CLARIFICATION_MODEL", "gemini-2.5-flash-lite")
    DISCOVERY_MODEL: str = os.getenv("DISCOVERY_MODEL", "gemini-2.5-flash-lite")
    EXTRACTION_MODEL: str = os.getenv("EXTRACTION_MODEL", "gemini-2.5-flash-lite")
    RETRIEVAL_MODEL: str = os.getenv("RETRIEVAL_MODEL", "gemini-2.5-flash-lite")
    
    # Database Settings (Target DB to query)
    DATABASE_URL: str = "sqlite:///./derivinsightnew.db"
    SCHEMA_PATH: str = "app/files/derivinsight_schema.sql"
    MOCK_DATA_SCRIPT_PATH: str = "app/files/generate_mock_data.py"
    
    # Cache / Redis (Valkey) Settings
    # Option A: Set REDIS_URL directly (e.g. rediss://:AUTH_TOKEN@host:6379/0)
    REDIS_URL: str = _DEFAULT_REDIS_URL
    # Option B: Build URL from parts (REDIS_HOST takes precedence over REDIS_URL)
    REDIS_HOST: Optional[str] = "hack-deriv-realtime-6ur8gt.serverless.aps1.cache.amazonaws.com"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_USE_SSL: bool = True  # Set True for AWS ElastiCache Valkey (in-transit encryption)
    REDIS_DB: int = 0

    @model_validator(mode="after")
    def build_redis_url_from_parts(self) -> "Settings":
        """If REDIS_HOST is set, build REDIS_URL from REDIS_* parts (for AWS Valkey)."""
        if not self.REDIS_HOST:
            return self
        scheme = "rediss"
        password = quote(self.REDIS_PASSWORD, safe="") if self.REDIS_PASSWORD else ""
        auth = f":{password}@" if password else ""
        self.REDIS_URL = f"{scheme}://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return self
    
    # ECS worker tasks (optional; if set, API can start/stop engine/generator via ECS)
    ECS_CLUSTER: Optional[str] = os.getenv("ECS_CLUSTER", "HackathonDerivBackend")
    ECS_TASK_DEFINITION: Optional[str] = os.getenv("ECS_TASK_DEFINITION", None) # single task def; command overridden per run
    ECS_ENGINE_TASK_DEFINITION: Optional[str] = os.getenv("ECS_ENGINE_TASK_DEFINITION", None)  # fallback if ECS_TASK_DEFINITION not set
    ECS_GENERATOR_TASK_DEFINITION: Optional[str] = os.getenv("ECS_GENERATOR_TASK_DEFINITION", None)
    ECS_ENGINE_WORKER_CONTAINER_NAME: str = "alerting-worker-container"  # MUST match container name in task definition
    ECS_GENERATOR_WORKER_CONTAINER_NAME: str = "event-generator-worker-container"
    
    ECS_SUBNETS: Optional[str] = os.getenv("ECS_SUBNETS", None)  # comma-separated subnet IDs
    ECS_SECURITY_GROUPS: Optional[str] = os.getenv("ECS_SECURITY_GROUPS", None)  # comma-separated security group IDs
    ECS_LAUNCH_TYPE: str = "FARGATE"
    
    # Sentinel v2 Feature Flags
    DEEP_DIVE_ENABLED: bool = True
    DEEP_DIVE_MAX_DEPTH: int = 2
    CORRELATION_ENABLED: bool = True
    ADAPTIVE_ENABLED: bool = True

    # Slack Alerts
    SLACK_WEBHOOK_URL: Optional[str] = None  # Legacy webhook (optional fallback)
    SLACK_BOT_TOKEN: Optional[str] = os.getenv("SLACK_BOT_TOKEN", None)    # Bot token (xoxb-...) for chat.postMessage API
    SLACK_CHANNEL: str = "sentinnelanomalies" # Default channel name
    SLACK_ALERT_MIN_SEVERITY: str = "HIGH"   # Minimum severity to trigger Slack (HIGH or CRITICAL)

    # App Settings
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
