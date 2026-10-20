import argparse
import asyncio
import contextlib
import json
import logging
import signal
import sys

from analyzer import SentimentAnalyzer
from config import settings
from db import DatabaseManager
from worker import SentimentWorker


def setup_logging():
    """Настройка структурированного логирования."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


async def test_single_article(news_id: int):
    """Тестовый анализ одной статьи по ID для проверки токена и модели."""
    db = DatabaseManager()
    await db.initialize()
    async with db.pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT id, title, content, description, source, categories FROM raw_news WHERE id = %s;", (news_id,)
        )
        row = await cur.fetchone()

    if not row:
        print(f"❌ Статья с ID {news_id} не найдена в базе данных.")
        await db.close()
        return

    n_id, title, content, desc, source, cats = row
    print(f"\n📰 Анализ статьи ID {n_id}: {title}")
    print(f"🌐 Провайдер: {settings.llm_base_url} | Модель: {settings.llm_model}")
    print("⏳ Отправка запроса к модели по токену...")

    analyzer = SentimentAnalyzer()
    try:
        res = await analyzer.analyze_article(
            title=title,
            content=content or desc,
            source=source,
            categories=cats or [],
        )
        print("\n✅ Успешный ответ модели:")
        print(json.dumps(res.model_dump(), indent=2, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Ошибка анализа: {e}")
    finally:
        await db.close()


def main():
    parser = argparse.ArgumentParser(description="LLM News Sentiment Service")
    parser.add_argument("--token", "--api-key", dest="api_key", type=str, help="API токен (Groq / OpenAI / Cloud API)")
    parser.add_argument("--model", type=str, help="Имя модели (например, llama-3.3-70b-versatile)")
    parser.add_argument("--base-url", type=str, help="URL эндпоинта (например, https://api.groq.com/openai/v1)")
    parser.add_argument("--test-id", type=int, help="Протестировать токен на 1 статье по ID без запуска демона")

    args = parser.parse_args()

    if args.api_key:
        settings.llm_api_key = args.api_key
        if args.api_key.startswith("gsk_"):
            if not args.base_url and ("11434" in settings.llm_base_url or "127.0.0.1" in settings.llm_base_url):
                settings.llm_base_url = "https://api.groq.com/openai/v1"
            if not args.model and settings.llm_model == "deepseek-r1:14b":
                settings.llm_model = "llama-3.3-70b-versatile"

    if args.base_url:
        settings.llm_base_url = args.base_url
    if args.model:
        settings.llm_model = args.model

    setup_logging()

    if args.test_id:
        asyncio.run(test_single_article(args.test_id))
        return

    worker = SentimentWorker()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Регистрация обработчиков сигналов остановки
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop)

    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
