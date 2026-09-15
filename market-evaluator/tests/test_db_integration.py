"""Интеграционные тесты работы с базой данных PostgreSQL.

Проверяют реальное исполнение SQL-запросов и структуру таблиц.
Если PostgreSQL недоступен, тесты аккуратно пропускаются.
"""

import pytest
from config import settings
from db import DatabaseManager


@pytest.mark.asyncio
async def test_database_connection_and_stats():
    """Проверка подключения к PostgreSQL и выполнения аналитического SQL-запроса."""
    db = DatabaseManager()
    try:
        await db.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL недоступен для интеграционного теста: {e}")

    try:
        # Проверяем исполнение сложного SQL-запроса get_stats
        stats = await db.get_stats()
        assert isinstance(stats, dict)
        # Проверяем наличие ключевых полей агрегации
        assert "total_evaluations" in stats
        assert "factual_evals" in stats
        assert "speculative_evals" in stats
        assert "avg_volume_surge" in stats
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_fetch_unevaluated_news_query():
    """Проверка корректности синтаксиса и выполнения FETCH_UNEVALUATED_NEWS_QUERY."""
    db = DatabaseManager()
    try:
        await db.initialize()
    except Exception as e:
        pytest.skip(f"PostgreSQL недоступен для интеграционного теста: {e}")

    try:
        news_list = await db.fetch_unevaluated_news(limit=5)
        assert isinstance(news_list, list)
        for item in news_list:
            assert "news_id" in item
            assert "title" in item
            assert "timestamp_utc" in item
            assert "llm_result" in item
    finally:
        await db.close()
