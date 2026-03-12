import os
from fastapi import FastAPI

from api.health import router as health_router
from api.ingest import router as ingest_router
from api.reports import router as reports_router
from api.admin_devices import router as admin_devices_router

from infra.settings import settings
from infra.migrate import apply_migrations




def create_app():
    app = FastAPI(title=settings.POS_APP_NAME)

    app.include_router(health_router)
    app.include_router(ingest_router)
    app.include_router(reports_router)
    app.include_router(admin_devices_router)

    @app.on_event("startup")
    def on_startup():
        base_dir = os.path.dirname(__file__)
        migrations_dir = os.path.join(base_dir, "migrations")

        ok, err = apply_migrations(migrations_dir)
        if not ok:
            raise RuntimeError("Migration failed: " + err)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9000, reload=False)
