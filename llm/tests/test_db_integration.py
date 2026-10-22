import asyncio

import psycopg
import pytest
from db import DatabaseManager


async def _get_connected_db():
    db = DatabaseManager()
    try:
        await db.initialize()
        async with asyncio.timeout(2.0):
            async with db.pool.connection() as conn, conn.cursor() as cur:
                await cur.execute("SELECT 1;")
        return db
    except (psycopg.Error, TimeoutError, OSError) as e:
        if db.pool:
            await db.close()
        pytest.skip(f"PostgreSQL недоступен для теста: {e}")


@pytest.mark.asyncio
async def test_llm_db_connection_and_stats():
    """Проверка подключения к PostgreSQL и выполнения статистики по raw_news."""
    db = await _get_connected_db()
    try:
        stats = await db.get_stats()
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "processed" in stats
        assert "unprocessed" in stats
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_fetch_unprocessed_batch_query():
    """Проверка запроса выборки пачки новостей."""
    db = await _get_connected_db()
    try:
        batch = await db.fetch_unprocessed_batch(limit=2)
        assert isinstance(batch, list)
        for item in batch:
            assert "id" in item
            assert "market" in item
            assert "title" in item
            assert "content" in item
            assert "source" in item

        # Проверка выборки с фильтрацией по рынку
        moex_batch = await db.fetch_unprocessed_batch(limit=2, market="moex")
        assert isinstance(moex_batch, list)
        for item in moex_batch:
            assert item["market"] == "moex"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_save_llm_error():
    """Проверка сохранения информации об ошибке анализа без сбоя пайплайна."""
    db = await _get_connected_db()

    try:
        # Вставляем временную тестовую новость
        async with db.pool.connection() as conn, conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO raw_news (url, title, source, content, timestamp_utc, processed)
                VALUES ('https://test.com/error_test', 'Error Test', 'Test', 'Content', NOW(), FALSE)
                ON CONFLICT (url) DO UPDATE SET processed = FALSE, llm_result = NULL
                RETURNING id;
                """
            )
            test_id = (await cur.fetchone())[0]
            await conn.commit()

        # Сохраняем ошибку
        await db.save_llm_error(news_id=test_id, error_message="Test context size error")

        # Проверяем, что статья помечена processed = TRUE и содержит error в llm_result
        from psycopg.rows import dict_row

        async with db.pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT processed, llm_result FROM raw_news WHERE id = %s;", (test_id,))
            row = await cur.fetchone()
            assert row["processed"] is True
            assert "error" in row["llm_result"]
            assert row["llm_result"]["error"] == "Test context size error"
            assert "failed_at" in row["llm_result"]

            # Очищаем тестовую запись
            await cur.execute("DELETE FROM raw_news WHERE id = %s;", (test_id,))
            await conn.commit()
    finally:
        await db.close()
