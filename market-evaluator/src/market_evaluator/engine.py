"""Математический движок анализа событийного окна (Event Study Engine)."""

import logging
from datetime import datetime
from typing import List, Optional, Tuple
from market_evaluator.config import settings
from market_evaluator.models import Candle, EventStudyMetrics

logger = logging.getLogger(__name__)


class EventStudyEngine:
    """Расчет количественных метрик влияния новости на котировки актива."""

    @classmethod
    def compute(
        cls,
        candles: List[Candle],
        t0_timestamp: datetime,
        ticker: str,
        symbol: str,
        sentiment_label: str,
        sentiment_score: float,
        impact_magnitude: int,
    ) -> Optional[EventStudyMetrics]:
        """Вычисляет полный набор метрик доходностей, просадок и точности прогноза."""
        if not candles:
            logger.warning("Нет свечей для расчета метрик по %s в момент %s", symbol, t0_timestamp)
            return None

        # 1. Поиск свечи в момент публикации новости t0
        t0_ms = int(t0_timestamp.timestamp() * 1000)
        t0_idx = min(range(len(candles)), key=lambda i: abs(int(candles[i].timestamp.timestamp() * 1000) - t0_ms))
        t0_candle = candles[t0_idx]

        p0 = t0_candle.close
        if p0 <= 0:
            return None

        # Разделяем на фазы: ДО новости и ПОСЛЕ новости
        pre_candles = candles[:t0_idx]
        post_candles = candles[t0_idx:]

        if not pre_candles or not post_candles:
            logger.warning("Недостаточно свечей до или после события для %s", symbol)
            return None

        # 2. Метрики ДО новости (Pre-event)
        pre_open = pre_candles[0].open
        pre_drift_pct = ((p0 - pre_open) / pre_open) * 100.0 if pre_open > 0 else 0.0

        pre_volumes = [c.volume for c in pre_candles]
        avg_pre_vol = sum(pre_volumes) / len(pre_volumes) if pre_volumes else 1.0
        t0_vol = t0_candle.volume
        volume_surge_ratio = t0_vol / avg_pre_vol if avg_pre_vol > 0 else 1.0

        # 3. Метрики ПОСЛЕ новости (Post-event горизонты)
        def calc_return_at(offset_minutes: int) -> Optional[float]:
            target_ms = t0_ms + offset_minutes * 60 * 1000
            # Ищем свечу
            matching = [c for c in post_candles if int(c.timestamp.timestamp() * 1000) >= target_ms]
            if not matching:
                # Еще не наступил этот момент времени
                return None
            target_candle = matching[0]
            return ((target_candle.close - p0) / p0) * 100.0

        ret_15m = calc_return_at(15)
        ret_1h = calc_return_at(60)
        ret_2h = calc_return_at(120)
        ret_4h = calc_return_at(240)
        ret_8h = calc_return_at(480)
        ret_24h = calc_return_at(1440)

        # 4. Экстремумы (Max Run-up, Max Drawdown, Размах)
        post_highs = [c.high for c in post_candles]
        post_lows = [c.low for c in post_candles]
        max_high = max(post_highs)
        min_low = min(post_lows)

        max_runup_pct = ((max_high - p0) / p0) * 100.0
        max_drawdown_pct = ((min_low - p0) / p0) * 100.0
        volatility_range_pct = ((max_high - min_low) / p0) * 100.0

        # 5. Проверка согласованности направления (Directional Alignment)
        def check_alignment(ret: Optional[float]) -> Optional[bool]:
            if ret is None:
                return None
            lbl = sentiment_label.lower()
            thresh = settings.neutral_threshold_pct
            if lbl == "bullish" or sentiment_score > 0.1:
                return ret > thresh
            elif lbl == "bearish" or sentiment_score < -0.1:
                return ret < -thresh
            else:  # neutral
                return abs(ret) <= thresh

        aligned_15m = check_alignment(ret_15m)
        aligned_1h = check_alignment(ret_1h)
        aligned_4h = check_alignment(ret_4h)
        aligned_24h = check_alignment(ret_24h)

        detail = {
            "candle_interval": settings.candle_interval,
            "candles_count": len(candles),
            "t0_candle_time": t0_candle.timestamp.isoformat(),
            "max_high_price": max_high,
            "min_low_price": min_low,
            "avg_pre_volume": round(avg_pre_vol, 2),
            "t0_volume": round(t0_vol, 2),
        }

        return EventStudyMetrics(
            ticker=ticker,
            symbol=symbol,
            t0_timestamp=t0_timestamp,
            p0_price=round(p0, 4),
            pre_drift_pct=round(pre_drift_pct, 3),
            volume_surge_ratio=round(volume_surge_ratio, 2),
            return_15m_pct=round(ret_15m, 3) if ret_15m is not None else None,
            return_1h_pct=round(ret_1h, 3) if ret_1h is not None else None,
            return_2h_pct=round(ret_2h, 3) if ret_2h is not None else None,
            return_4h_pct=round(ret_4h, 3) if ret_4h is not None else None,
            return_8h_pct=round(ret_8h, 3) if ret_8h is not None else None,
            return_24h_pct=round(ret_24h, 3) if ret_24h is not None else None,
            max_runup_pct=round(max_runup_pct, 3),
            max_drawdown_pct=round(max_drawdown_pct, 3),
            volatility_range_pct=round(volatility_range_pct, 3),
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            impact_magnitude=impact_magnitude,
            is_aligned_15m=aligned_15m,
            is_aligned_1h=aligned_1h,
            is_aligned_4h=aligned_4h,
            is_aligned_24h=aligned_24h,
            metrics_detail=detail,
        )
