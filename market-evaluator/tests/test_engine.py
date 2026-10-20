"""Тесты математического движка анализа событий (EventStudyEngine)."""

from datetime import UTC, datetime, timedelta

from engine import EventStudyEngine

from models import Candle, EventStudyMetrics


def generate_candle_series(
    t0_dt: datetime,
    pre_count: int = 16,  # 4 часа до (16 свечей по 15м)
    post_count: int = 96,  # 24 часа после (96 свечей по 15м)
    base_price: float = 100.0,
    price_path: list[float] | None = None,
    t0_volume_multiplier: float = 3.0,
) -> list[Candle]:
    """Генерирует синтетический ряд 15-минутных свечей вокруг момента события t0."""
    start_dt = t0_dt - timedelta(minutes=pre_count * 15)
    total_count = pre_count + 1 + post_count
    candles = []

    for i in range(total_count):
        candle_dt = start_dt + timedelta(minutes=i * 15)

        # Объем: средний 10.0, на свече t0 (индекс pre_count) всплеск
        volume = 10.0
        if i == pre_count:
            volume = 10.0 * t0_volume_multiplier

        # Цена
        p = price_path[i] if price_path is not None and i < len(price_path) else base_price

        candles.append(
            Candle(
                timestamp=candle_dt,
                open=p,
                high=p * 1.002,
                low=p * 0.998,
                close=p,
                volume=volume,
            )
        )

    return candles


def test_compute_bullish_impact_confirmed():
    """Тест: бычья новость приводит к росту цены и всплеску объема (гипотеза подтверждена)."""
    t0 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)

    # 4 свечи до (по 100.0), свеча t0 (100.0, объем x3.0),
    # через 1 час (4 свечи после t0) цена вырастает до 105.0 (+5%),
    # через 4 часа (16 свечей после t0) цена держится на 108.0 (+8%).
    candles = generate_candle_series(
        t0_dt=t0,
        pre_count=16,
        post_count=96,
        base_price=100.0,
        t0_volume_multiplier=3.0,
    )

    # Модифицируем цены после t0:
    t0_idx = 16
    for i in range(t0_idx + 1, len(candles)):
        candles[i].open = 105.0
        candles[i].close = 105.0
        candles[i].high = 108.0
        candles[i].low = 99.5

    # Устанавливаем цену на горизонте 4h (15 свечей после t0 закрывается ровно в t0 + 4h)
    candles[t0_idx + 15].close = 107.0
    candles[t0_idx + 15].high = 110.0

    metrics = EventStudyEngine.compute(
        candles=candles,
        t0_timestamp=t0,
        ticker="BTC",
        symbol="BTCUSDT",
        sentiment_label="BULLISH",
        sentiment_score=0.85,
        impact_magnitude=3,
        target_horizon_hours=4,
        is_mean_reverting=False,
        is_speculative=False,
    )

    assert metrics is not None
    assert isinstance(metrics, EventStudyMetrics)
    assert metrics.ticker == "BTC"
    assert metrics.symbol == "BTCUSDT"
    assert metrics.p0_price == 100.0

    # Проверка всплеска объема: на t0 объем 30, средний до t0 был 10 -> ratio = 3.0
    assert metrics.volume_surge_ratio == 3.0

    # Проверка доходностей
    assert metrics.return_1h_pct == 5.0  # (105 - 100) / 100 = +5%
    assert metrics.return_4h_pct == 7.0  # (107 - 100) / 100 = +7%

    # Экстремумы
    assert metrics.max_runup_pct == 10.0  # High 110 / 100 = +10%
    assert metrics.max_drawdown_pct == -0.5  # Low 99.5 / 100 = -0.5%

    # Подтверждение импульса (порог 0.2%, факт +10%)
    assert metrics.is_impulse_confirmed is True

    # Согласованность направления: на 1h и 4h модель предсказала рост и цена выросла
    assert metrics.is_aligned_1h is True
    assert metrics.is_aligned_4h is True
    assert metrics.is_target_horizon_aligned is True

    # Флаг спекулятивности
    assert metrics.is_speculative is False


def test_compute_bearish_failed_prediction():
    """Тест: медвежья новость, но цена вопреки прогнозу выросла (ошибка модели)."""
    t0 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    candles = generate_candle_series(t0_dt=t0, pre_count=16, post_count=96, base_price=100.0)

    # Цена на t0 и после новости только растет (low не падает ниже 100.0)
    t0_idx = 16
    candles[t0_idx].low = 100.0
    for i in range(t0_idx + 1, len(candles)):
        candles[i].open = 106.0
        candles[i].close = 106.0
        candles[i].high = 107.0
        candles[i].low = 105.5

    metrics = EventStudyEngine.compute(
        candles=candles,
        t0_timestamp=t0,
        ticker="ETH",
        symbol="ETHUSDT",
        sentiment_label="BEARISH",
        sentiment_score=-0.75,
        impact_magnitude=2,
        target_horizon_hours=1,
        is_mean_reverting=False,
        is_speculative=True,
    )

    assert metrics is not None
    # Медвежий импульс НЕ подтвердился (просадки ниже -0.2% не было)
    assert metrics.is_impulse_confirmed is False
    # Согласованность направления отрицательная
    assert metrics.is_aligned_1h is False
    assert metrics.is_target_horizon_aligned is False
    # Флаг спекулятивности сохранен
    assert metrics.is_speculative is True


def test_compute_mean_reverting():
    """Тест: новость с ожиданием возврата к среднему (mean-reversion)."""
    t0 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    candles = generate_candle_series(t0_dt=t0, pre_count=16, post_count=96, base_price=100.0)

    # Начальный импульс: первые 2 свечи взлетают до 105.0
    t0_idx = 16
    candles[t0_idx + 1].close = 104.0
    candles[t0_idx + 1].high = 106.0
    candles[t0_idx + 2].close = 105.0
    candles[t0_idx + 2].high = 107.0

    # К горизонту 4 часа (t0_idx + 16) цена полностью откатывается назад к 100.05
    for i in range(t0_idx + 10, len(candles)):
        candles[i].open = 100.05
        candles[i].close = 100.05
        candles[i].high = 100.1
        candles[i].low = 99.95

    metrics = EventStudyEngine.compute(
        candles=candles,
        t0_timestamp=t0,
        ticker="SOL",
        symbol="SOLUSDT",
        sentiment_label="BULLISH",
        sentiment_score=0.8,
        impact_magnitude=3,
        target_horizon_hours=4,
        is_mean_reverting=True,
        is_speculative=False,
    )

    assert metrics is not None
    assert metrics.is_impulse_confirmed is True  # Импульс был (+7% high)
    # На 4h горизонте цена вернулась к P0 (100.05 vs 100.00 = +0.05% <= 0.3% порог)
    assert metrics.is_target_horizon_aligned is True


def test_compute_insufficient_candles():
    """Тест: обработка граничных случаев (пустой список свечей)."""
    t0 = datetime(2026, 1, 15, 12, 0, 0, tzinfo=UTC)
    res = EventStudyEngine.compute(
        candles=[],
        t0_timestamp=t0,
        ticker="BTC",
        symbol="BTCUSDT",
        sentiment_label="BULLISH",
        sentiment_score=0.5,
        impact_magnitude=1,
    )
    assert res is None
