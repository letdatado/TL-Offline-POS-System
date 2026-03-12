from fastapi import APIRouter

from infra.db import db_ping

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/db")
def health_db():
    ok, err = db_ping()
    if ok:
        return {"db": "ok"}
    return {"db": "error", "detail": err}
