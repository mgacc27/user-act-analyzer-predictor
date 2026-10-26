"""Расчет бизнес-метрик: DAU, MAU, средняя длительность сессий, события по типам."""
from datetime import timedelta
import pandas as pd

def compute_metrics(df: pd.DataFrame, period_start, period_end,
                    overload_threshold: float = 5000.0) -> dict:
    lo = pd.Timestamp(period_start)
    hi = pd.Timestamp(period_end) + timedelta(days=1)
    part = df.loc[(df["event_ts"] >= lo) & (df["event_ts"] < hi)]
    out = {"period_start": str(lo.date()), "period_end": str(hi.date()),
           "dau": 0, "mau": 0, "avg_session_sec": None,
           "events_by_type": {}, "peak_hour": None, "is_overload": False}
    if part.empty:
        return out
    daily = part.groupby(part["event_ts"].dt.date)["user_ref"].nunique()
    out["dau"] = int(round(daily.mean()))
    out["mau"] = int(part.loc[part["event_ts"] >= hi - timedelta(days=30), "user_ref"].nunique())
    type_col = "type_code" if "type_code" in part.columns else "event_type"
    sess = part.loc[part[type_col] == "session_start", "session_duration_sec"].dropna()
    out["avg_session_sec"] = round(float(sess.mean()), 2) if not sess.empty else None
    out["events_by_type"] = {k: int(v) for k, v in part[type_col].value_counts().items()}
    hourly = part.groupby(part["event_ts"].dt.hour).size()
    out["peak_hour"] = int(hourly.idxmax())
    out["is_overload"] = bool(hourly.max() > overload_threshold)
    return out