"""Загрузка SQL-запросов из внешних .sql файлов."""

from pathlib import Path

# Директория со всеми sql-файлами сервиса
SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql"


def _read_sql_file(filename: str) -> str:
    file_path = SQL_DIR / filename
    if not file_path.is_file():
        raise FileNotFoundError(f"SQL-файл не найден: {file_path}")
    return file_path.read_text(encoding="utf-8").strip()


FETCH_UNPROCESSED_BATCH_QUERY = _read_sql_file("fetch_unprocessed_batch.sql")
SAVE_LLM_RESULT_QUERY = _read_sql_file("save_llm_result.sql")
GET_TABLE_STATS_QUERY = _read_sql_file("get_table_stats.sql")
