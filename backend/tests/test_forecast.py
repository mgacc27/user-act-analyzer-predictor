import pytest
from app.services.forecast import (HoltWinters, ForecastError, backtest, mape, rmse, wma)

def test_mape_known():
    assert mape([100, 200], [110, 190]) == 7.5

def test_rmse_known():
    assert rmse([1, 2, 3], [1, 2, 5]) == pytest.approx(1.15, abs=0.01)

def test_wma_lag7():
    assert wma([1, 2, 3, 4, 5, 6, 7]) == 5.0        # sum(i*i)/sum(i) = 140/28

def test_hw_predict_length(seasonal_series):
    pred = HoltWinters().fit(seasonal_series).predict(14)
    assert len(pred) == 14 and all(v >= 0 for v in pred)

@pytest.mark.parametrize("h", [0, 15, -3])
def test_horizon_limit_raises(h):
    with pytest.raises(ForecastError):
        HoltWinters().fit([1.0] * 30).predict(h)

def test_backtest_acceptable(seasonal_series):
    bt = backtest(seasonal_series, 14)
    assert bt.is_acceptable and bt.mape <= 8.0       # целевой критерий ТЗ

def test_backtest_no_future_leakage(seasonal_series):
    corrupted = seasonal_series[:-14] + [v * 10 for v in seasonal_series[-14:]]
    bt = backtest(corrupted, 14)
    control = mape(corrupted[-14:], HoltWinters().fit(corrupted[:-14]).predict(14))
    assert bt.mape == control                        # обучение только на прошлом

def test_short_history_raises():
    with pytest.raises(ForecastError):
        backtest([100.0] * 20, 14)