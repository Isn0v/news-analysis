"""Загрузка SQL-запросов из внешних .sql файлов."""

from pathlib import Path

# Директория со всеми sql-файлами сервиса
SQL_DIR = Path(__file__).resolve().parent / "sql"


def _read_sql_file(filename: str) -> str:
    file_path = SQL_DIR / filename
    if not file_path.is_file():
        raise FileNotFoundError(f"SQL-файл не найден: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


FETCH_UNPROCESSED_BATCH_QUERY = _read_sql_file("fetch_unprocessed_batch.sql")
FETCH_UNPROCESSED_BATCH_BY_MARKET_QUERY = _read_sql_file("fetch_unprocessed_batch_by_market.sql")
SAVE_LLM_RESULT_QUERY = _read_sql_file("save_llm_result.sql")
RELEASE_ARTICLE_LOCK_QUERY = _read_sql_file("release_article_lock.sql")
GET_TABLE_STATS_QUERY = _read_sql_file("get_table_stats.sql")
FETCH_NEWS_BY_ID_QUERY = _read_sql_file("fetch_news_by_id.sql")
