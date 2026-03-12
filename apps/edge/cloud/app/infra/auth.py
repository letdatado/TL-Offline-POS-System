from fastapi import Header, HTTPException

from infra.settings import settings


def require_ingest_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    """
    If CLOUD_INGEST_API_KEY is set (non-empty), require matching X-API-Key header.
    If it's empty, allow all (dev mode).
    """
    required = settings.CLOUD_INGEST_API_KEY

    if required is None:
        required = ""

    required = required.strip()

    if required == "":
        return  # auth disabled

    if x_api_key is None:
        raise HTTPException(status_code=401, detail="missing api key")

    if x_api_key.strip() != required:
        raise HTTPException(status_code=401, detail="invalid api key")