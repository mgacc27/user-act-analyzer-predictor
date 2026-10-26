from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.api.routes import router
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base, engine, SessionLocal
from app.db.models import User

def seed() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User).limit(1)):
            db.add_all([User(login="admin", password_hash=hash_password("admin"), role="ADMIN"),
                        User(login="analyst", password_hash=hash_password("analyst"), role="USER")])
            db.commit()

def create_app() -> FastAPI:
    app = FastAPI(title="Activity Forecast", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                       allow_methods=["GET", "POST"], allow_headers=["Authorization"])
    app.include_router(router)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}
    return app

seed()
app = create_app()