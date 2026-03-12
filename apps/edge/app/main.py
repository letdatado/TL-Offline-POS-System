import os
from fastapi import FastAPI

from api.health import router as health_router
from api.products import router as products_router
from api.cart import router as cart_router
from api.checkout import router as checkout_router
from api.outbox import router as outbox_router
from api.dispatch import router as dispatch_router
from api.sync import router as sync_router
from api.mock_cloud import router as mock_cloud_router
from api.inventory import router as inventory_router
# from api.reports import router as reports_router

from infra.settings import settings
from infra.migrate import apply_migrations
from infra.events import register_handler

from modules.retail_inventory import handle_order_paid


def create_app():
    app = FastAPI(title=settings.POS_APP_NAME)

    # Routes
    app.include_router(health_router)
    app.include_router(products_router)
    app.include_router(cart_router)
    app.include_router(checkout_router)
    app.include_router(outbox_router)
    app.include_router(dispatch_router)
    app.include_router(sync_router)
    app.include_router(mock_cloud_router)
    app.include_router(inventory_router)
    # app.include_router(reports_router)




    @app.on_event("startup")
    def on_startup():
        # Apply DB migrations at startup
        base_dir = os.path.dirname(__file__)
        migrations_dir = os.path.join(base_dir, "migrations")

        ok, err = apply_migrations(migrations_dir)
        if not ok:
            # Fail fast: if schema is broken, don't run a POS server.
            raise RuntimeError("Migration failed: " + err)
        register_handler("order.paid", handle_order_paid)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
