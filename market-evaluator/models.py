"""Модели данных и структуры для сервиса market-evaluator."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Candle(BaseModel):
    """Модель биржевой свечи OHLCV."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class EventStudyMetrics(BaseModel):
    """Результаты расчета квантитативных метрик поведения актива вокруг новости."""
    ticker: str
    symbol: str
    t0_timestamp: datetime
    p0_price: float
    pre_drift_pct: float
    volume_surge_ratio: float

    # Доходности на горизонтах
    return_15m_pct: Optional[float] = None
    return_1h_pct: Optional[float] = None
    return_2h_pct: Optional[float] = None
    return_4h_pct: Optional[float] = None
    return_8h_pct: Optional[float] = None
    return_24h_pct: Optional[float] = None

    # Экстремумы
    max_runup_pct: float
    max_drawdown_pct: float
    volatility_range_pct: float

    # Оценки модели
    sentiment_label: str
    sentiment_score: float
    impact_magnitude: int
    target_horizon_hours: int = 4
    is_mean_reverting_expected: bool = False

    # Согласованность с прогнозом
    is_impulse_confirmed: Optional[bool] = None
    is_target_horizon_aligned: Optional[bool] = None
    is_aligned_15m: Optional[bool] = None
    is_aligned_1h: Optional[bool] = None
    is_aligned_4h: Optional[bool] = None
    is_aligned_24h: Optional[bool] = None

    # Дополнительные детали
    metrics_detail: Dict[str, Any] = Field(default_factory=dict)
