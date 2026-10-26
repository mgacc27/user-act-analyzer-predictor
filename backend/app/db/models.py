import uuid
from datetime import datetime, date
from sqlalchemy import (String, Boolean, Integer, SmallInteger, Numeric, DateTime, Date,
                        ForeignKey, UniqueConstraint, CheckConstraint, Text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass

def _uuid() -> str: return str(uuid.uuid4())

class User(Base):
    __tablename__ = "app_user"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    login: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(72), nullable=False)   # bcrypt
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

class ImportBatch(Base):
    __tablename__ = "import_batch"
    batch_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.user_id"), nullable=False)
    format_name: Mapped[str] = mapped_column(String(10), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_error: Mapped[str | None] = mapped_column(Text)

class LogRecord(Base):   
    __tablename__ = "log_record"
    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batch.batch_id"), nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    user_ref: Mapped[str] = mapped_column(String(64), nullable=False)
    type_code: Mapped[str] = mapped_column(String(20), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(36))
    session_duration_sec: Mapped[float | None] = mapped_column(Numeric(10, 2))
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class Forecast(Base):
    __tablename__ = "forecast"
    forecast_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    horizon_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    model_name: Mapped[str] = mapped_column(String(40), nullable=False, default="HOLT_WINTERS")
    __table_args__ = (CheckConstraint("horizon_days BETWEEN 1 AND 14"),)

class ForecastPoint(Base):
    __tablename__ = "forecast_point"
    point_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(ForeignKey("forecast.forecast_id", ondelete="CASCADE"), nullable=False)
    point_date: Mapped[date] = mapped_column(Date, nullable=False)
    predicted_value: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_overload_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    __table_args__ = (UniqueConstraint("forecast_id", "point_date"),)

class BacktestResult(Base):
    __tablename__ = "backtest_result"
    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_id: Mapped[str] = mapped_column(ForeignKey("forecast.forecast_id", ondelete="CASCADE"),
                                             nullable=False, unique=True)
    mape: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    rmse: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    is_acceptable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

class Report(Base):
    __tablename__ = "report"
    report_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("app_user.user_id"), nullable=False)
    forecast_id: Mapped[str | None] = mapped_column(ForeignKey("forecast.forecast_id"))
    format_name: Mapped[str] = mapped_column(String(10), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)