"""Маршруты API модульного монолита (FastAPI)."""
import time
from datetime import date, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (create_access_token, current_user,
                               require_admin, verify_password)
from app.db.base import get_db
from app.db.models import (BacktestResult, Forecast, ForecastPoint,
                           ImportBatch, LogRecord, Report, User)
from app.services import etl
from app.services import forecast as fsvc
from app.services import metrics as msvc
from app.services import reports as rsvc

router = APIRouter(prefix="/api/v1")


def load_logs_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(LogRecord)).all()
    if not rows:
        return pd.DataFrame(columns=["event_ts", "user_ref", "type_code",
                                     "session_id", "session_duration_sec",
                                     "is_anomaly"])
    data = []
    for r in rows:
        data.append({
            "event_ts": r.event_ts,
            "user_ref": r.user_ref,
            "type_code": r.type_code,
            "session_id": r.session_id,
            "session_duration_sec": (float(r.session_duration_sec)
                                     if r.session_duration_sec is not None else None),
            "is_anomaly": r.is_anomaly,
        })
    return pd.DataFrame(data)


def holidays_set() -> set:
    return {date.fromisoformat(d) for d in settings.holidays.split(",") if d}


@router.post("/auth/token")
def login(form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.login == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Неверный логин или пароль")
    return {"access_token": create_access_token(user.user_id, user.role),
            "token_type": "bearer"}


@router.post("/data/import", status_code=201)
@router.post("/data/import", status_code=201)
def import_logs(file: UploadFile = File(...), db: Session = Depends(get_db),
                user: dict = Depends(current_user)):
    try:
        content = file.file.read()
        fmt = (file.filename.rsplit(".", 1)[-1].lower()
               if file.filename and "." in file.filename else "?")
        
        df = etl.validate_records(etl.parse_file(content, file.filename or ""))
        
        series, flags = etl.preprocess(df, holidays_set(),
                                       settings.z_window_days, settings.z_threshold)
        flag_by_date = {ts.date(): bool(v) for ts, v in flags.items()}

        batch = ImportBatch(user_id=user["sub"], format_name=fmt,
                            file_name=file.filename or "?", record_count=len(df))
        db.add(batch)
        db.flush()
        
        for row in df.itertuples():
            # Жесткое приведение времени к стандартному datetime Python
            ts = pd.Timestamp(row.event_ts)
            event_ts_dt = ts.to_pydatetime()
            event_ts_date = ts.date()

            # Безопасная обработка session_id
            sid = getattr(row, "session_id", None)
            if sid is None or (isinstance(sid, float) and pd.isna(sid)) or str(sid).strip() == "" or str(sid).lower() == "nan":
                sid = None
                
            # Безопасная обработки длительности сессии
            dur = getattr(row, "session_duration_sec", None)
            if dur is None or (isinstance(dur, float) and pd.isna(dur)) or str(dur).lower() == "nan":
                dur = None
            else:
                dur = float(dur)

            db.add(LogRecord(
                batch_id=batch.batch_id,
                event_ts=event_ts_dt,
                user_ref=str(row.user_id)[:64],
                type_code=str(row.event_type)[:20],
                session_id=sid,
                session_duration_sec=dur,
                is_anomaly=flag_by_date.get(event_ts_date, False),
            ))
        db.commit()
        return {"imported": len(df), "anomalies_marked": int(flags.sum())}
        
    except etl.ValidationError as exc:
        raise HTTPException(422, str(exc))
    except Exception as exc:
        # Если произошла ЛЮБАЯ другая ошибка, мы выводим её текст прямо на фронтенд!
        import traceback
        error_detail = f"Внутренняя ошибка импорта: {str(exc)}\n{traceback.format_exc()}"
        raise HTTPException(500, detail=error_detail)


@router.get("/data/history")
def history(db: Session = Depends(get_db), user: dict = Depends(current_user)):
    df = load_logs_df(db)
    if df.empty:
        return []
    series, flags = etl.preprocess(df, holidays_set())
    train = etl.training_series(series, flags)
    return [{"date": str(ts.date()), "value": float(v),
             "is_anomaly": bool(flags.get(ts, False))}
            for ts, v in train.items()]


@router.get("/metrics")
def get_metrics(start: str | None = None, end: str | None = None,
                db: Session = Depends(get_db), user: dict = Depends(current_user)):
    df = load_logs_df(db)
    end = end or str(date.today())
    start = start or str(date.today() - timedelta(days=30))
    return msvc.compute_metrics(df, start, end)


@router.get("/forecast/predict")
def predict(days: int = Query(14), db: Session = Depends(get_db),
            user: dict = Depends(current_user)):
    if not 1 <= days <= settings.forecast_horizon_max:
        raise HTTPException(422, "Горизонт прогноза допустим в пределах 1..14 дней (FR-04)")
    t0 = time.perf_counter()
    df = load_logs_df(db)
    if df.empty:
        raise HTTPException(422, "Недостаточно данных: импортируйте логи")
    series, flags = etl.preprocess(df, holidays_set())
    train_series = etl.training_series(series, flags)
    try:
        points_vals, bt, stability = fsvc.make_forecast(train_series.tolist(), days)
    except fsvc.ForecastError as exc:
        raise HTTPException(422, str(exc))
    mean, std = train_series.mean(), train_series.std()
    fc = Forecast(user_id=user["sub"], horizon_days=days)
    db.add(fc)
    db.flush()
    out = []
    for i, v in enumerate(points_vals):
        risk = bool(v > mean + 2 * std)
        db.add(ForecastPoint(forecast_id=fc.forecast_id,
                             point_date=date.today() + timedelta(days=i + 1),
                             predicted_value=v, is_overload_risk=risk))
        out.append({"date": str(date.today() + timedelta(days=i + 1)),
                    "value": v, "is_overload_risk": risk})
    db.add(BacktestResult(forecast_id=fc.forecast_id, mape=bt.mape,
                          rmse=bt.rmse, is_acceptable=bt.is_acceptable))
    db.commit()
    return {"points": out, "mape": bt.mape, "rmse": bt.rmse,
            "is_acceptable": bt.is_acceptable,
            "wma_stability": round(stability, 2),
            "elapsed_sec": round(time.perf_counter() - t0, 3)}


@router.get("/reports/export")
@router.get("/reports/export")
def export(format: str = Query("pdf"), db: Session = Depends(get_db),
           user: dict = Depends(current_user)):
    if format not in rsvc.ALLOWED:
        raise HTTPException(422, "Допустимые форматы: pdf, xlsx")
    df = load_logs_df(db)
    if df.empty:
        raise HTTPException(422, "Недостаточно данных для отчета")
    series, flags = etl.preprocess(df, holidays_set())
    train = etl.training_series(series, flags)
    points_vals, bt, _ = fsvc.make_forecast(train.tolist())
    mean, std = train.mean(), train.std()
    points = [{"date": str(date.today() + timedelta(days=i + 1)), "value": v,
               "is_overload_risk": bool(v > mean + 2 * std)}
              for i, v in enumerate(points_vals)]
    mets = msvc.compute_metrics(df, str(series.index.min().date()),
                                str(series.index.max().date()))
    db.add(Report(user_id=user["sub"], format_name=format, file_name=f"report.{format}"))
    db.commit()
    if format == "xlsx":
        return Response(
            rsvc.build_xlsx(mets, points, bt),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=report.xlsx"})
    return Response(rsvc.build_pdf(mets, points, bt, train.tolist(),
                                   [str(d.date()) for d in train.index]),
                    media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=report.pdf"})


@router.get("/admin/performance")
def performance(db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return {"logs": db.query(LogRecord).count(),
            "batches": db.query(ImportBatch).count(),
            "forecasts": db.query(Forecast).count()}