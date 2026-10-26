import pandas as pd
import pytest
from app.services.metrics import compute_metrics

@pytest.fixture
def mdf() -> pd.DataFrame:
    r = [
        ("2026-10-01 10:00", "u1", "click", None), ("2026-10-01 10:30", "u2", "view", None),
        ("2026-10-01 11:00", "u3", "session_start", 100),
        ("2026-10-02 10:00", "u2", "view", None), ("2026-10-02 12:00", "u3", "purchase", None),
        ("2026-10-03 10:00", "u1", "session_start", 200),
    ]
    return pd.DataFrame([(pd.Timestamp(a), b, c, d) for a, b, c, d in r],
                        columns=["event_ts", "user_ref", "type_code", "session_duration_sec"])

def test_dau(mdf):
    assert compute_metrics(mdf, "2026-10-01", "2026-10-03")["dau"] == 2 

def test_mau(mdf):
    assert compute_metrics(mdf, "2026-10-01", "2026-10-03")["mau"] == 3

def test_avg_session(mdf):
    assert compute_metrics(mdf, "2026-10-01", "2026-10-03")["avg_session_sec"] == 150.0

def test_events_by_type(mdf):
    e = compute_metrics(mdf, "2026-10-01", "2026-10-03")["events_by_type"]
    assert e == {"view": 2, "session_start": 2, "click": 1, "purchase": 1}

def test_peak_hour(mdf):
    assert compute_metrics(mdf, "2026-10-01", "2026-10-03")["peak_hour"] == 10

@pytest.mark.parametrize("thr,expected", [(10**9, False), (1, True)])
def test_overload_flag(mdf, thr, expected):
    assert compute_metrics(mdf, "2026-10-01", "2026-10-03", thr)["is_overload"] is expected

def test_empty_period(mdf):
    out = compute_metrics(mdf, "2025-01-01", "2025-01-31")
    assert (out["dau"], out["mau"], out["is_overload"]) == (0, 0, False)