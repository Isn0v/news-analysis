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
FETCH_NEWS_BY_ID_QUERY = _read_sql("fetch_news_by_id.sql")
MARK_NEWS_EVALUATED_QUERY = _read_sql("mark_news_evaluated.sql")
GET_MODEL_STATS_QUERY = _read_sql("get_model_stats.sql")
RECALCULATE_FETCH_ALL_QUERY = _read_sql("recalculate_fetch_all.sql")
RECALCULATE_UPDATE_IMPACT_QUERY = _read_sql("recalculate_update_impact.sql")
EXPORT_RAW_NEWS_QUERY = _read_sql("export_raw_news.sql")
EXPORT_MARKET_IMPACT_QUERY = _read_sql("export_market_impact.sql")
EXPORT_COMBINED_QUERY = _read_sql("export_combined.sql")
