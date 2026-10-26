"""Импорт и предобработка логов: парсинг .csv/.json, валидация,
скользящий Z-score (окно 7 дней), линейная интерполяция пропусков."""
import csv, io, json
from datetime import date
import pandas as pd

REQUIRED_COLUMNS = {"event_ts", "user_id", "event_type"}
ALLOWED_EXT = {".csv", ".json"}
ALLOWED_TYPES = {"click", "view", "purchase", "session_start"}

class ValidationError(ValueError):
    """Ошибка структуры файла -> HTTP 422 без аварийного завершения (NFR-R-03)."""

def parse_file(content: bytes, filename: str) -> list[dict]:
    ext = filename[filename.rfind("."):].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise ValidationError(f"Неподдерживаемый формат '{ext or 'без расширения'}': ожидался .csv или .json")
    try:
        if ext == ".csv":
            rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
        else:
            data = json.loads(content.decode("utf-8"))
            rows = data["records"] if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValidationError("Корневой элемент файла должен быть массивом записей")
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise ValidationError(f"Файл повреждён: {exc}") from exc
    return rows

def validate_records(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        raise ValidationError("Файл не содержит ни одной записи")
    df = pd.DataFrame(rows)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValidationError(f"Отсутствуют обязательные колонки: {', '.join(sorted(missing))}")
    df["event_ts"] = pd.to_datetime(df["event_ts"], errors="coerce")
    if df["event_ts"].isna().any():
        raise ValidationError("Колонка event_ts содержит неразборные даты")
    unknown = set(df["event_type"].dropna().astype(str).unique()) - ALLOWED_TYPES
    if unknown:
        raise ValidationError(f"Неизвестные типы событий: {', '.join(map(str, unknown))}")
    # Безопасное создание колонок, если их нет в CSV
    if "session_id" not in df.columns:
        df["session_id"] = None
    if "session_duration_sec" not in df.columns:
        df["session_duration_sec"] = None
    else:
        df["session_duration_sec"] = pd.to_numeric(df["session_duration_sec"], errors="coerce")
    return df

def daily_series(df: pd.DataFrame) -> pd.Series:
    """Дневной ряд активности; работает и с CSV-именами, и с именами БД."""
    col = "user_ref" if "user_ref" in df.columns else "user_id"
    return df.set_index("event_ts")[col].resample("D").size().rename("value")

def fill_gaps(series: pd.Series) -> pd.Series:
    """Технические пропуски заполняются линейной интерполяцией (FR-02)."""
    idx = pd.date_range(series.index.min(), series.index.max(), freq="D")
    return series.reindex(idx).interpolate(method="linear", limit_direction="both")

def mark_anomalies(series: pd.Series, holidays: set[date] | None = None,
                   window: int = 7, threshold: float = 3.0) -> pd.Series:
    """|x_t - mu_t| > 3*sigma_t по предшествующему окну 7 дней;
    праздничные пики аномалиями не считаются (контекстная проверка)."""
    holidays = holidays or set()
    prev = series.shift(1)
    mu = prev.rolling(window, min_periods=window).mean()
    sigma = prev.rolling(window, min_periods=window).std(ddof=0).replace(0, pd.NA)
    flags = ((series - mu).abs() / sigma > threshold).fillna(False).astype(bool)
    holiday_mask = pd.Series([d.date() in holidays for d in series.index], index=series.index)
    return flags & ~holiday_mask

def preprocess(df: pd.DataFrame, holidays=None, window=7, threshold=3.0):
    series = fill_gaps(daily_series(df))
    return series, mark_anomalies(series, holidays, window, threshold)

def training_series(series: pd.Series, flags: pd.Series) -> pd.Series:
    """Для обучения аномалии временно интерполируются соседними периодами (FR-02)."""
    return series.mask(flags).interpolate(method="linear", limit_direction="both")