#!/usr/bin/env python3
"""Скрипт централизованной миграции базы данных PostgreSQL."""

import os
import socket
import sys
from pathlib import Path

# Корень репозитория
ROOT_DIR = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = ROOT_DIR / "migrations"


def load_env_file(filepath: Path):
    """Простая загрузка переменных из .env без внешних зависимостей."""
    if not filepath.is_file():
        return
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if key not in os.environ:
            os.environ[key] = val


def resolve_postgres_host(configured_host: str) -> str:
    """Если хост указан как 'db' (для Docker), но скрипт запущен на хосте, заменяем на localhost."""
    if configured_host == "db":
        try:
            socket.gethostbyname("db")
            return "db"
        except socket.gaierror:
            return "localhost"
    return configured_host


def run_migrations():
    load_env_file(ROOT_DIR / ".env")

    db_host = resolve_postgres_host(os.getenv("POSTGRES_HOST", "localhost"))
    db_port = int(os.getenv("POSTGRES_PORT", "5432"))
    db_user = os.getenv("POSTGRES_USER", "trader")
    db_password = os.getenv("POSTGRES_PASSWORD", "")
    db_name = os.getenv("POSTGRES_DB", "crypto_news")

    if not db_password:
        print("❌ Ошибка: POSTGRES_PASSWORD не найден в .env или переменных окружения.")
        sys.exit(1)

    print("==========================================================")
    print("📦 Централизованная миграция базы данных")
    print(f"База:  {db_user}@{db_host}:{db_port}/{db_name}")
    print(f"Папка: {MIGRATIONS_DIR}")
    print("==========================================================")

    import psycopg

    dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    try:
        with psycopg.connect(dsn, autocommit=True) as conn, conn.cursor() as cur:
            # 1. Создаем таблицу учета миграций, если ее еще нет
            cur.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)

            # 2. Получаем список уже примененных миграций
            cur.execute("SELECT version FROM schema_migrations;")
            applied = {row[0] for row in cur.fetchall()}

            # 3. Ищем все .sql файлы в migrations/
            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
            if not migration_files:
                print("⚠️ В папке migrations/ нет .sql файлов.")
                return

            new_count = 0
            for sql_file in migration_files:
                version = sql_file.name
                if version in applied:
                    print(f"  ⏭️  [ПРОПУСК] {version} (уже применена)")
                    continue

                print(f"  🚀 [ПРИМЕНЕНИЕ] {version}...")
                sql_content = sql_file.read_text(encoding="utf-8")

                with conn.transaction():
                    cur.execute(sql_content)
                    cur.execute(
                        "INSERT INTO schema_migrations (version) VALUES (%s);",
                        (version,),
                    )

                print(f"  ✅ [УСПЕХ] {version} успешно применена!")
                new_count += 1

            print("----------------------------------------------------------")
            if new_count > 0:
                print(f"🎉 Успешно применено новых миграций: {new_count}")
            else:
                print("✨ База данных актуальна, новых миграций нет.")

    except psycopg.OperationalError as e:
        print(f"❌ Не удалось подключиться к PostgreSQL ({db_host}:{db_port}): {e}")
        print("💡 Убедитесь, что база запущена: docker compose up -d db")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"❌ Ошибка применения миграции: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
