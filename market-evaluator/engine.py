"""Математический движок анализа событийного окна (Event Study Engine)."""

import logging
from datetime import datetime

from config import settings

from models import Candle, EventStudyMetrics

logger = logging.getLogger(__name__)


class EventStudyEngine:
    """Расчет количественных метрик влияния новости на котировки актива."""

    @classmethod
    def compute(
        cls,
        candles: list[Candle],
        t0_timestamp: datetime,
        ticker: str,
        symbol: str,
        sentiment_label: str,
        sentiment_score: float,
        impact_magnitude: int,
        target_horizon_hours: int = 4,
        is_mean_reverting: bool = False,
        is_speculative: bool = False,
        llm_model: str = "unknown",
    ) -> EventStudyMetrics | None:
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

        candle_duration_ms = 15 * 60 * 1000

        # 3. Метрики ПОСЛЕ новости (Post-event горизонты)
        def calc_return_at(offset_minutes: int) -> float | None:
            target_ms = t0_ms + offset_minutes * 60 * 1000
            # Ищем первую свечу, закрытие которой произошло в target_ms или позже
            matching = [
                c for c in post_candles if (int(c.timestamp.timestamp() * 1000) + candle_duration_ms) >= target_ms
            ]
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

        # 4. Экстремумы (Max Run-up, Max Drawdown, Размах за весь период наблюдения)
        post_highs = [c.high for c in post_candles]
        post_lows = [c.low for c in post_candles]
        max_high = max(post_highs)
        min_low = min(post_lows)

        max_runup_pct = ((max_high - p0) / p0) * 100.0
        max_drawdown_pct = ((min_low - p0) / p0) * 100.0
        volatility_range_pct = ((max_high - min_low) / p0) * 100.0

        # 5. Оценка подтверждения первичного импульса (строго в окне первых 2 часов от t0)
        thresh = settings.neutral_threshold_pct
        lbl = sentiment_label.lower()

        impulse_window_ms = 2 * 60 * 60 * 1000
        impulse_candles = [
            c for c in post_candles
            if (int(c.timestamp.timestamp() * 1000) - t0_ms) <= impulse_window_ms
        ]
        if not impulse_candles:
            impulse_candles = post_candles[:1]

        initial_high = max(c.high for c in impulse_candles)
        initial_low = min(c.low for c in impulse_candles)
        initial_runup_pct = ((initial_high - p0) / p0) * 100.0
        initial_drawdown_pct = ((initial_low - p0) / p0) * 100.0
        initial_volatility_range_pct = ((initial_high - initial_low) / p0) * 100.0

        if lbl == "bullish" or sentiment_score > 0.1:
            is_impulse_confirmed = initial_runup_pct >= thresh
        elif lbl == "bearish" or sentiment_score < -0.1:
            is_impulse_confirmed = initial_drawdown_pct <= -thresh
        else:
            # Для нейтральных событий: отсутствие аномального размаха в первые 2 часа
            is_impulse_confirmed = initial_volatility_range_pct <= (thresh * 2.0)

        # 6. Проверка согласованности направления (Directional Alignment)
        def check_alignment(ret: float | None) -> bool | None:
            if ret is None:
                return None
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

        # 7. Адаптивная оценка под заявленный целевой горизонт (Target Horizon)
        if target_horizon_hours <= 1:
            target_ret = ret_1h
        elif target_horizon_hours <= 3:
            target_ret = ret_2h
        elif target_horizon_hours <= 6:
            target_ret = ret_4h
        elif target_horizon_hours <= 12:
            target_ret = ret_8h
        elif target_horizon_hours <= 24:
            target_ret = ret_24h
        else:
            target_ret = calc_return_at(target_horizon_hours * 60)

        # Определение траектории (Trajectory: CONTINUATION, FADED, ADVERSE, NO_IMPULSE)
        trajectory = "NO_IMPULSE"
        retrace_pct = 0.0

        if is_impulse_confirmed and (lbl == "bullish" or sentiment_score > 0.1):
            if target_ret is not None and target_ret >= thresh:
                trajectory = "CONTINUATION"
            elif target_ret is not None and initial_runup_pct > 0:
                retrace_pct = max(0.0, min(100.0, ((initial_runup_pct - target_ret) / initial_runup_pct) * 100.0))
                trajectory = "FADED" if retrace_pct >= 50.0 or target_ret <= (thresh * 0.5) else "CONTINUATION"
            else:
                trajectory = "FADED"
        elif is_impulse_confirmed and (lbl == "bearish" or sentiment_score < -0.1):
            if target_ret is not None and target_ret <= -thresh:
                trajectory = "CONTINUATION"
            elif target_ret is not None and initial_drawdown_pct < 0:
                retrace_pct = max(
                    0.0,
                    min(100.0, ((abs(initial_drawdown_pct) - abs(target_ret)) / abs(initial_drawdown_pct)) * 100.0),
                )
                trajectory = "FADED" if retrace_pct >= 50.0 or target_ret >= (-thresh * 0.5) else "CONTINUATION"
            else:
                trajectory = "FADED"
        elif (
            not is_impulse_confirmed
            and target_ret is not None
            and (
                ((lbl == "bullish" or sentiment_score > 0.1) and target_ret <= -thresh)
                or ((lbl == "bearish" or sentiment_score < -0.1) and target_ret >= thresh)
            )
        ):
            trajectory = "ADVERSE"

        if target_ret is None:
            is_target_horizon_aligned = None
        elif is_mean_reverting:
            # Ожидался откат: первичный импульс случился, и траектория откатила (FADED) либо вернулась к P0
            is_target_horizon_aligned = is_impulse_confirmed and (
                trajectory == "FADED" or (abs(target_ret) <= thresh * 1.5)
            )
        else:
            is_target_horizon_aligned = check_alignment(target_ret)

        detail = {
            "candle_interval": settings.candle_interval,
            "candles_count": len(candles),
            "t0_candle_time": t0_candle.timestamp.isoformat(),
            "max_high_price": max_high,
            "min_low_price": min_low,
            "initial_runup_pct": round(initial_runup_pct, 3),
            "initial_drawdown_pct": round(initial_drawdown_pct, 3),
            "initial_volatility_range_pct": round(initial_volatility_range_pct, 3),
            "trajectory": trajectory,
            "retrace_pct": round(retrace_pct, 1),
            "avg_pre_volume": round(avg_pre_vol, 2),
            "t0_volume": round(t0_vol, 2),
            "target_horizon_hours": target_horizon_hours,
            "target_return_pct": round(target_ret, 3) if target_ret is not None else None,
            "is_mean_reverting_expected": is_mean_reverting,
        }

        return EventStudyMetrics(
            ticker=ticker,
            symbol=symbol,
            llm_model=llm_model,
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
            target_horizon_hours=target_horizon_hours,
            is_mean_reverting_expected=is_mean_reverting,
            is_speculative=is_speculative,
            is_impulse_confirmed=is_impulse_confirmed,
            is_target_horizon_aligned=is_target_horizon_aligned,
            is_aligned_15m=aligned_15m,
            is_aligned_1h=aligned_1h,
            is_aligned_4h=aligned_4h,
            is_aligned_24h=aligned_24h,
            metrics_detail=detail,
        )
