"""Загрузка внешних SQL-запросов для сервиса market-evaluator."""

from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent / "sql"


def _read_sql(filename: str) -> str:
    path = SQL_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"SQL файл не найден: {path}")
    return path.read_text(encoding="utf-8").strip()


FETCH_UNEVALUATED_NEWS_QUERY = _read_sql("fetch_unevaluated_news.sql")
SAVE_MARKET_IMPACT_QUERY = _read_sql("save_market_impact.sql")
GET_EVALUATION_STATS_QUERY = _read_sql("get_evaluation_stats.sql")
SCHEMA_DDL = _read_sql("schema.sql")
