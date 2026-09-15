"""Интеграционные тесты работы с базой данных PostgreSQL для сервиса LLM."""

import pytest
from db import DatabaseManager


@pytest.mark.asyncio
async def test_llm_db_connection_and_stats():
    """Проверка подключения к PostgreSQL и выполнения статистики по raw_news."""
    db = DatabaseManager()
    try:
        await db.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL недоступен для теста: {e}")

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
    db = DatabaseManager()
    try:
        await db.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL недоступен для теста: {e}")

    try:
        batch = await db.fetch_unprocessed_batch(limit=2)
        assert isinstance(batch, list)
        for item in batch:
            assert "id" in item
            assert "title" in item
            assert "content" in item
            assert "source" in item
    finally:
        await db.close()
