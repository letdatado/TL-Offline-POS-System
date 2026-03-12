from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    POS_DB_DSN: str = "postgresql://pos:pos@localhost:5432/pos_edge"

    # App metadata
    POS_APP_NAME: str = "pos-edge"
    POS_ENV: str = "dev"

    # Device identity (used by sync)
    POS_DEVICE_ID: str = "edge-001"

    # Cloud base URL (real cloud should be http://localhost:9000)
    # Keep this as a sensible default and override via .env for server deployments.
    POS_CLOUD_URL: str = "http://localhost:9000"

    # Cloud ingest API key (Batch 12)
    # If empty, Edge will NOT send X-API-Key header.
    POS_CLOUD_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()



