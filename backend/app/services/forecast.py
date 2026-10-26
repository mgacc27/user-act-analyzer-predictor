"""Прогнозирование: Хольта-Винтерс (тренд + сезонность 7 дней), резервный WMA (лаг 7),
метрики MAPE/RMSE, хронологический бэктест на скрытом 14-дневном окне."""
import math
from dataclasses import dataclass

MAX_HORIZON, MAPE_TARGET, SEASON = 14, 8.0, 7

class ForecastError(ValueError): ...

@dataclass
class Backtest:
    mape: float
    rmse: float
    is_acceptable: bool

def mape(actual, pred) -> float:
    pairs = [(a, p) for a, p in zip(actual, pred) if a != 0]
    return round(100.0 * sum(abs(a - p) / abs(a) for a, p in pairs) / len(pairs), 2) if pairs else 0.0

def rmse(actual, pred) -> float:
    return round(math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, pred)) / len(actual)), 2) if actual else 0.0

class HoltWinters:
    """Аддитивное тройное экспоненциальное сглаживание."""
    def __init__(self, season: int = SEASON, alpha=0.3, beta=0.1, gamma=0.3):
        self.season, self.alpha, self.beta, self.gamma = season, alpha, beta, gamma
        self.l = self.b = None
        self.s: list[float] = []

    def fit(self, y: list[float]) -> "HoltWinters":
        m = self.season
        if len(y) < 2 * m:
            raise ForecastError(f"Недостаточно истории: нужно >= {2 * m} точек, получено {len(y)}")
        self.l = sum(y[:m]) / m
        self.b = (sum(y[m:2 * m]) - sum(y[:m])) / (m * m)
        self.s = [y[i] - self.l for i in range(m)]
        for t in range(m, len(y)):
            s_prev, l_prev = self.s[t - m], self.l
            self.l = self.alpha * (y[t] - s_prev) + (1 - self.alpha) * (l_prev + self.b)
            self.b = self.beta * (self.l - l_prev) + (1 - self.beta) * self.b
            self.s.append(self.gamma * (y[t] - self.l) + (1 - self.gamma) * s_prev)
        return self

    def predict(self, horizon: int) -> list[float]:
        if not 1 <= horizon <= MAX_HORIZON:
            raise ForecastError("Горизонт прогноза допустим в пределах 1..14 дней (FR-04)")
        if self.l is None:
            raise ForecastError("Модель не обучена")
        m, n = self.season, len(self.s)
        return [round(max(0.0, self.l + h * self.b + self.s[n - m + ((h - 1) % m)]), 2)
                for h in range(1, horizon + 1)]

def wma(series: list[float], lag: int = 7) -> float:
    """Резервный метод: взвешенное скользящее среднее с лагом 7 дней."""
    if len(series) < lag:
        raise ForecastError(f"Для WMA нужно >= {lag} точек")
    weights = range(1, lag + 1)
    return sum(w * v for w, v in zip(weights, series[-lag:])) / sum(weights)

def backtest(series: list[float], horizon: int = 14) -> Backtest:
    """Ретроспективный контроль: скрытый отрезок в конце ряда, данные из будущего не используются."""
    if len(series) <= horizon + 2 * SEASON:
        raise ForecastError("Недостаточно истории для бэктестинга")
    train, hold = series[:-horizon], series[-horizon:]
    pred = HoltWinters().fit(train).predict(horizon)
    m = mape(hold, pred)
    return Backtest(m, rmse(hold, pred), m <= MAPE_TARGET)

def make_forecast(series: list[float], horizon: int = 14):
    bt = backtest(series)
    model = HoltWinters().fit(series)
    points = model.predict(horizon)
    stability = wma(series)          # экспресс-оценка стабильности ряда (резервный метод)
    return points, bt, stability