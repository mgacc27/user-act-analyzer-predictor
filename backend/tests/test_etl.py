from datetime import date
import pandas as pd
import pytest
from app.services import etl

def test_parse_csv_ok(sample_csv, sample_rows):
    assert len(etl.parse_file(sample_csv, "logs.csv")) == len(sample_rows)

def test_parse_json_ok(sample_rows):
    blob = b'{"records": ' + pd.DataFrame(sample_rows).to_json(orient="records").encode() + b"}"
    assert len(etl.parse_file(blob, "logs.json")) == len(sample_rows)

@pytest.mark.parametrize("name", ["log.txt", "log.xml", "log"])
def test_parse_wrong_format_raises(name):
    with pytest.raises(etl.ValidationError):
        etl.parse_file(b"x", name)

def test_parse_corrupted_json_raises():
    with pytest.raises(etl.ValidationError, match="поврежд"):
        etl.parse_file(b"{not json", "a.json")

def test_validate_missing_column_raises():
    with pytest.raises(etl.ValidationError, match="обязательные колонки"):
        etl.validate_records([{"event_ts": "2026-01-01", "user_id": "u1"}])

def test_validate_bad_date_raises():
    with pytest.raises(etl.ValidationError, match="event_ts"):
        etl.validate_records([{"event_ts": "вчера", "user_id": "u1", "event_type": "click"}])

def test_validate_unknown_event_type_raises():
    with pytest.raises(etl.ValidationError, match="типы событий"):
        etl.validate_records([{"event_ts": "2026-01-01 10:00", "user_id": "u1",
                               "event_type": "hack"}])

def test_fill_gaps_linear():
    # Создаем ряд с пропуском посередине: 1-е и 3-е число есть, 2-го нет
    idx = pd.to_datetime(["2026-01-01", "2026-01-03"])
    s = pd.Series([10.0, 30.0], index=idx)
    filled = etl.fill_gaps(s)
    # Линейная интерполяция между 10 и 30 должна дать ровно 20
    assert filled.loc["2026-01-02"] == pytest.approx(20.0)

SPIKE_DAY = 40  # Явно задаем константу для теста

def test_mark_anomalies_flags_spike(sample_rows):
    df = etl.validate_records(sample_rows)
    series, flags = etl.preprocess(df)
    spike_date = pd.Timestamp(etl.daily_series(df).index[0]) + pd.Timedelta(days=SPIKE_DAY)
    assert flags.sum() >= 1
    assert bool(flags.loc[spike_date]) is True

def test_mark_anomalies_holiday_exempt(sample_rows):
    df = etl.validate_records(sample_rows)
    series = etl.fill_gaps(etl.daily_series(df))
    spike_date = series.index[40].date()
    flags = etl.mark_anomalies(series, holidays={spike_date})
    assert flags.sum() == 0                                    # контекстная проверка календаря

def test_history_preserved_full_volume(sample_rows):
    df = etl.validate_records(sample_rows)
    n_before = len(df)
    etl.preprocess(df)
    assert len(df) == n_before                                 # удаление данных запрещено 