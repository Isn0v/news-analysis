"""Асинхронная работа с PostgreSQL для чтения необработанных новостей и записи результатов."""

import json
import logging
from typing import List, Dict, Any, Optional
from psycopg_pool import AsyncConnectionPool

from llm.config import settings
from llm.schema import SentimentAnalysisResult

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Менеджер подключений к PostgreSQL с пулом соединений."""

    def __init__(self):
        self.pool: Optional[AsyncConnectionPool] = None

    async def initialize(self):
        """Инициализирует пул асинхронных соединений."""
        logger.info("Подключение к PostgreSQL: %s:%s/%s...",
                    settings.postgres_host, settings.postgres_port, settings.postgres_db)
        self.pool = AsyncConnectionPool(
            conninfo=settings.postgres_dsn,
            min_size=1,
            max_size=10,
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
        query = """
        SELECT id, source, title, categories, description, content, timestamp_utc
        FROM raw_news
        WHERE processed = FALSE
        ORDER BY timestamp_utc DESC
        LIMIT %s;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (limit,))
                rows = await cur.fetchall()

                # Преобразуем строки в список словарей
                results = []
                for row in rows:
                    results.append({
                        "id": row[0],
                        "source": row[1],
                        "title": row[2],
                        "categories": row[3] or [],
                        "description": row[4] or "",
                        "content": row[5] or "",
                        "timestamp_utc": row[6],
                    })
                return results

    async def save_llm_result(self, news_id: int, result: SentimentAnalysisResult):
        """Сохраняет размеченный сентимент в JSONB-колонку llm_result и выставляет processed = TRUE."""
        query = """
        UPDATE raw_news
        SET processed = TRUE,
            processed_at = NOW(),
            llm_result = %s::jsonb
        WHERE id = %s;
        """
        result_json = result.model_dump_json()

        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, (result_json, news_id))
                await conn.commit()

    async def get_stats(self) -> Dict[str, int]:
        """Возвращает общую статистику по таблице raw_news."""
        query = """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE processed = TRUE) AS processed,
            COUNT(*) FILTER (WHERE processed = FALSE) AS unprocessed
        FROM raw_news;
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query)
                row = await cur.fetchone()
                return {
                    "total": row[0],
                    "processed": row[1],
                    "unprocessed": row[2],
                }
