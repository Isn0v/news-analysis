"""Асинхронная работа с PostgreSQL для чтения необработанных новостей и записи результатов."""

import logging
from typing import List, Dict, Any, Optional
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from llm.config import settings
from llm.schema import SentimentAnalysisResult
from llm.queries import (
    FETCH_UNPROCESSED_BATCH_QUERY,
    SAVE_LLM_RESULT_QUERY,
    GET_TABLE_STATS_QUERY,
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер подключений к PostgreSQL с пулом соединений."""

    def __init__(self):
        self.pool: Optional[AsyncConnectionPool] = None

    async def initialize(self):
        """Инициализирует пул асинхронных соединений."""
        logger.info(
            "Подключение к PostgreSQL: %s:%s/%s...",
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
        logger.info("Пул соединений PostgreSQL успешно открыт.")

    async def close(self):
        """Закрывает пул соединений."""
        if self.pool:
            await self.pool.close()
            logger.info("Пул соединений PostgreSQL закрыт.")

    async def fetch_unprocessed_batch(self, limit: int) -> List[Dict[str, Any]]:
        """Извлекает пачку необработанных новостей из таблицы raw_news."""
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(FETCH_UNPROCESSED_BATCH_QUERY, (limit,))
                return await cur.fetchall()

    async def save_llm_result(self, news_id: int, result: SentimentAnalysisResult):
        """Сохраняет размеченный сентимент в JSONB-колонку llm_result и выставляет processed = TRUE."""
        result_json = result.model_dump_json()

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SAVE_LLM_RESULT_QUERY, (result_json, news_id))
                await conn.commit()

    async def get_stats(self) -> Dict[str, int]:
        """Возвращает общую статистику по таблице raw_news."""
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(GET_TABLE_STATS_QUERY)
                return await cur.fetchone()
