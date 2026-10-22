"""Асинхронная работа с базой данных PostgreSQL для сервиса market-evaluator."""

import json
import logging
from typing import Any

from config import settings
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from queries import (
    FETCH_UNEVALUATED_NEWS_QUERY,
    GET_EVALUATION_STATS_QUERY,
    SAVE_MARKET_IMPACT_QUERY,
)

from models import EventStudyMetrics

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер подключений к PostgreSQL с пулом соединений."""

    def __init__(self):
        self.pool: AsyncConnectionPool | None = None

    async def initialize(self):
        """Инициализирует пул соединений и проверяет наличие таблиц."""
        logger.info(
            "Подключение market-evaluator к PostgreSQL: %s:%s/%s...",
            settings.postgres_host,
            settings.postgres_port,
            settings.postgres_db,
        )
        self.pool = AsyncConnectionPool(
            conninfo=settings.postgres_dsn,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            open=False,
        )
        await self.pool.open()
        logger.info("Пул соединений PostgreSQL для market-evaluator открыт.")

    async def close(self):
        """Закрывает пул соединений."""
        if self.pool:
            await self.pool.close()
            logger.info("Пул соединений закрыт.")

    async def fetch_unevaluated_news(self, limit: int) -> list[dict[str, Any]]:
        """Запрашивает пачку новостей, ожидающих оценки рыночного влияния."""
        async with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(FETCH_UNEVALUATED_NEWS_QUERY, (limit,))
            return await cur.fetchall()

    async def fetch_news_by_id(self, news_id: int) -> dict[str, Any] | None:
        """Извлекает конкретную новость по ее ID."""
        query = """
        SELECT id AS news_id, source, title, timestamp_utc, llm_result
        FROM raw_news
        WHERE id = %s;
        """
        async with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, (news_id,))
            return await cur.fetchone()

    async def save_market_impact(self, news_id: int, metrics: EventStudyMetrics):
        """Сохраняет вычисленный Event Study результат в news_market_impact."""
        params = {
            "news_id": news_id,
            "ticker": metrics.ticker,
            "symbol": metrics.symbol,
            "llm_model": metrics.llm_model,
            "t0_timestamp": metrics.t0_timestamp,
            "p0_price": metrics.p0_price,
            "pre_drift_pct": metrics.pre_drift_pct,
            "volume_surge_ratio": metrics.volume_surge_ratio,
            "return_15m_pct": metrics.return_15m_pct,
            "return_1h_pct": metrics.return_1h_pct,
            "return_2h_pct": metrics.return_2h_pct,
            "return_4h_pct": metrics.return_4h_pct,
            "return_8h_pct": metrics.return_8h_pct,
            "return_24h_pct": metrics.return_24h_pct,
            "max_runup_pct": metrics.max_runup_pct,
            "max_drawdown_pct": metrics.max_drawdown_pct,
            "volatility_range_pct": metrics.volatility_range_pct,
            "sentiment_label": metrics.sentiment_label,
            "sentiment_score": metrics.sentiment_score,
            "impact_magnitude": metrics.impact_magnitude,
            "target_horizon_hours": metrics.target_horizon_hours,
            "is_mean_reverting_expected": metrics.is_mean_reverting_expected,
            "is_impulse_confirmed": metrics.is_impulse_confirmed,
            "is_target_horizon_aligned": metrics.is_target_horizon_aligned,
            "is_speculative": metrics.is_speculative,
            "is_aligned_15m": metrics.is_aligned_15m,
            "is_aligned_1h": metrics.is_aligned_1h,
            "is_aligned_4h": metrics.is_aligned_4h,
            "is_aligned_24h": metrics.is_aligned_24h,
            "metrics_detail": json.dumps(metrics.metrics_detail),
        }

        async with self.pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(SAVE_MARKET_IMPACT_QUERY, params)
            await conn.commit()

    async def mark_news_evaluated(self, news_id: int):
        """Помечает новость как оцененную (или проверенную) в raw_news."""
        query = """
        UPDATE raw_news
        SET market_evaluated = TRUE,
            market_evaluated_at = NOW()
        WHERE id = %s;
        """
        async with self.pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(query, (news_id,))
            await conn.commit()

    async def get_stats(self) -> dict[str, Any]:
        """Возвращает агрегированную аналитику точности и доходностей."""
        async with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(GET_EVALUATION_STATS_QUERY)
            return await cur.fetchone() or {}

    async def get_model_stats(self) -> list[dict[str, Any]]:
        """Возвращает сравнительную статистику точности по каждой LLM-модели."""
        query = """
        SELECT
            COALESCE(llm_model, 'unknown') AS model,
            COUNT(*) AS total_evals,
            COUNT(*) FILTER (WHERE is_speculative = FALSE) AS factual_evals,
            ROUND(AVG(volume_surge_ratio), 2) AS avg_vol_surge,
            ROUND(
                COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 /
                NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
                1
            ) AS factual_impulse_pct,
            ROUND(
                COUNT(*) FILTER (WHERE is_aligned_4h = TRUE AND is_speculative = FALSE)::numeric * 100.0 /
                NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND is_aligned_4h IS NOT NULL AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
                1
            ) AS factual_dir_4h_pct,
            ROUND(
                COUNT(*) FILTER (WHERE is_speculative = TRUE AND metrics_detail->>'trajectory' = 'FADED')::numeric * 100.0 /
                NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND is_impulse_confirmed = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
                1
            ) AS fade_rate_pct
        FROM news_market_impact
        GROUP BY COALESCE(llm_model, 'unknown')
        ORDER BY total_evals DESC;
        """
        async with self.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query)
            return await cur.fetchall()

    async def recalculate_all_impacts(self, thresh: float) -> int:
        """Пересчитывает подтверждение импульса, направленность и траектории для всех записей по порогу thresh."""
        fetch_query = """
        SELECT
            id,
            sentiment_label,
            sentiment_score,
            return_15m_pct,
            return_1h_pct,
            return_2h_pct,
            return_4h_pct,
            return_8h_pct,
            return_24h_pct,
            target_horizon_hours,
            is_mean_reverting_expected,
            is_speculative,
            metrics_detail
        FROM news_market_impact;
        """
        update_query = """
        UPDATE news_market_impact
        SET
            is_impulse_confirmed = %s,
            is_aligned_15m = %s,
            is_aligned_1h = %s,
            is_aligned_4h = %s,
            is_aligned_24h = %s,
            is_target_horizon_aligned = %s,
            metrics_detail = %s
        WHERE id = %s;
        """

        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(fetch_query)
                rows = await cur.fetchall()

            updates = []
            for row in rows:
                lbl = (row["sentiment_label"] or "").lower()
                sentiment_score = row["sentiment_score"] or 0.0
                target_horizon_hours = row["target_horizon_hours"] or 24
                is_mean_reverting = bool(row["is_mean_reverting_expected"])
                detail = dict(row["metrics_detail"]) if row["metrics_detail"] else {}

                initial_runup = float(detail.get("initial_runup_pct") or 0.0)
                initial_drawdown = float(detail.get("initial_drawdown_pct") or 0.0)
                initial_volatility = float(detail.get("initial_volatility_range_pct") or 0.0)
                target_ret_saved = detail.get("target_return_pct")
                target_ret_saved = float(target_ret_saved) if target_ret_saved is not None else None

                is_bullish = lbl == "bullish" or sentiment_score > 0.1
                is_bearish = lbl == "bearish" or sentiment_score < -0.1

                def to_float(val: Any) -> float | None:
                    return float(val) if val is not None else None

                ret_15m = to_float(row["return_15m_pct"])
                ret_1h = to_float(row["return_1h_pct"])
                ret_2h = to_float(row["return_2h_pct"])
                ret_4h = to_float(row["return_4h_pct"])
                ret_8h = to_float(row["return_8h_pct"])
                ret_24h = to_float(row["return_24h_pct"])

                # 1. Подтверждение первичного импульса
                if is_bullish:
                    is_impulse_confirmed = initial_runup >= thresh
                elif is_bearish:
                    is_impulse_confirmed = initial_drawdown <= -thresh
                else:
                    is_impulse_confirmed = initial_volatility <= (thresh * 2.0)

                # 2. Направленная согласованность (Directional Alignment)
                def check_alignment(ret: float | None, is_bull: bool, is_bear: bool) -> bool | None:
                    if ret is None:
                        return None
                    if is_bull:
                        return ret > thresh
                    elif is_bear:
                        return ret < -thresh
                    else:
                        return abs(ret) <= thresh

                aligned_15m = check_alignment(ret_15m, is_bullish, is_bearish)
                aligned_1h = check_alignment(ret_1h, is_bullish, is_bearish)
                aligned_4h = check_alignment(ret_4h, is_bullish, is_bearish)
                aligned_24h = check_alignment(ret_24h, is_bullish, is_bearish)

                # 3. Выбор целевой доходности под горизонт
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
                    target_ret = target_ret_saved

                # 4. Траектория
                trajectory = "NO_IMPULSE"
                retrace_pct = 0.0

                if is_impulse_confirmed and is_bullish:
                    if target_ret is not None and target_ret >= thresh:
                        trajectory = "CONTINUATION"
                    elif target_ret is not None and initial_runup > 0:
                        retrace_pct = max(0.0, min(100.0, ((initial_runup - target_ret) / initial_runup) * 100.0))
                        trajectory = "FADED" if retrace_pct >= 50.0 or target_ret <= (thresh * 0.5) else "CONTINUATION"
                    else:
                        trajectory = "FADED"
                elif is_impulse_confirmed and is_bearish:
                    if target_ret is not None and target_ret <= -thresh:
                        trajectory = "CONTINUATION"
                    elif target_ret is not None and initial_drawdown < 0:
                        retrace_pct = max(
                            0.0,
                            min(100.0, ((abs(initial_drawdown) - abs(target_ret)) / abs(initial_drawdown)) * 100.0),
                        )
                        trajectory = "FADED" if retrace_pct >= 50.0 or target_ret >= (-thresh * 0.5) else "CONTINUATION"
                    else:
                        trajectory = "FADED"
                elif (
                    not is_impulse_confirmed
                    and target_ret is not None
                    and ((is_bullish and target_ret <= -thresh) or (is_bearish and target_ret >= thresh))
                ):
                    trajectory = "ADVERSE"

                # 5. Целевой горизонт
                if target_ret is None:
                    is_target_horizon_aligned = None
                elif is_mean_reverting:
                    is_target_horizon_aligned = is_impulse_confirmed and (
                        trajectory == "FADED" or (abs(target_ret) <= thresh * 1.5)
                    )
                else:
                    is_target_horizon_aligned = check_alignment(target_ret, is_bullish, is_bearish)

                detail["trajectory"] = trajectory
                detail["retrace_pct"] = round(retrace_pct, 1)

                updates.append(
                    (
                        is_impulse_confirmed,
                        aligned_15m,
                        aligned_1h,
                        aligned_4h,
                        aligned_24h,
                        is_target_horizon_aligned,
                        json.dumps(detail),
                        row["id"],
                    )
                )

            async with conn.cursor() as cur:
                await cur.executemany(update_query, updates)
            await conn.commit()

            return len(updates)
