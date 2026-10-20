"""Асинхронная работа с PostgreSQL для чтения необработанных новостей и записи результатов."""

import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from config import settings
from schema import SentimentAnalysisResult
from queries import (
    FETCH_UNPROCESSED_BATCH_QUERY,
    SAVE_LLM_RESULT_QUERY,
    RELEASE_ARTICLE_LOCK_QUERY,
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

    async def fetch_unprocessed_batch(
        self,
        limit: int,
        worker_id: Optional[str] = None,
        lock_timeout_minutes: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Извлекает и атомарно блокирует пачку необработанных новостей (SKIP LOCKED)."""
        wid = worker_id or settings.worker_id
        timeout = lock_timeout_minutes or settings.lock_timeout_minutes
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(FETCH_UNPROCESSED_BATCH_QUERY, (limit, timeout, wid))
                return await cur.fetchall()

    async def release_locks(self, news_ids: List[int]):
        """Снимает блокировку со статей, если их обработка была прервана."""
        if not news_ids:
            return
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(RELEASE_ARTICLE_LOCK_QUERY, (news_ids,))
                await conn.commit()

    async def save_llm_result(self, news_id: int, result: SentimentAnalysisResult):
        """Сохраняет размеченный сентимент в JSONB-колонку llm_result и выставляет processed = TRUE."""
        result_json = result.model_dump_json()

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SAVE_LLM_RESULT_QUERY, (result_json, news_id))
                await conn.commit()

    async def save_llm_error(self, news_id: int, error_message: str):
        """Сохраняет статус ошибки для статьи, чтобы избежать бесконечного зацикливания воркера."""
        error_payload = json.dumps({
            "error": error_message,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        })

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SAVE_LLM_RESULT_QUERY, (error_payload, news_id))
                await conn.commit()

    async def get_stats(self) -> Dict[str, int]:
        """Возвращает общую статистику по таблице raw_news."""
        async with self.pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(GET_TABLE_STATS_QUERY)
                return await cur.fetchone()
