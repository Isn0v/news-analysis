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
