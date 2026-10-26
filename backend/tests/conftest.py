import csv, io, math, sys
from datetime import datetime, timedelta
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.security import hash_password
from app.db.base import Base, get_db
from app.db.models import User
from app.main import create_app

START = datetime(2026, 8, 1)
SPIKE_DAY = 40            # имитация DDoS-всплеска
DAYS = 60

def _rows(with_spike: bool = True) -> list[dict]:
    rows, types = [], ["click", "view", "purchase", "session_start"]
    for d in range(DAYS):
        day = START + timedelta(days=d)
        count = 100 + 40 * (day.weekday() >= 5) + (d % 3)      # недельная сезонность
        if with_spike and d == SPIKE_DAY:
            count *= 8
        for i in range(count):
            ts = day.replace(hour=i % 24, minute=i % 60)
            t = types[i % 4]
            rows.append({"event_ts": ts.isoformat(sep=" "), "user_id": f"u{i % 60}",
                         "event_type": t,
                         "session_id": f"s{d}-{i}" if t == "session_start" else "",
                         "session_duration_sec": str(60 + i % 240) if t == "session_start" else ""})
    return rows

@pytest.fixture(scope="session")
def sample_rows(): return _rows()

@pytest.fixture(scope="session")
def sample_csv(sample_rows) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["event_ts", "user_id", "event_type",
                                        "session_id", "session_duration_sec"])
    w.writeheader(); w.writerows(sample_rows)
    return buf.getvalue().encode()

@pytest.fixture(scope="session")
def seasonal_series() -> list[float]:
    return [100 + 0.5 * t + (40 if t % 7 >= 5 else 0) + 5 * math.sin(t / 3.0) for t in range(120)]

@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    app = create_app()
    app.dependency_overrides[get_db] = lambda: Session()
    with Session() as s:
        s.add_all([User(user_id="u-admin", login="admin", password_hash=hash_password("admin"), role="ADMIN"),
                   User(user_id="u-1", login="analyst", password_hash=hash_password("analyst"), role="USER")])
        s.commit()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def auth(client) -> dict:
    r = client.post("/api/v1/auth/token", data={"username": "analyst", "password": "analyst"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}