"""Скрипт перерасчета метрик для всех уже оцененных новостей в базе с новым движком."""

import asyncio
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "market-evaluator"))

from worker import MarketEvaluationWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    worker = MarketEvaluationWorker()
    await worker.initialize()

    # Извлекаем все news_id, присутствующие в news_market_impact
    async with worker.db.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT DISTINCT news_id FROM news_market_impact ORDER BY news_id;")
            rows = await cur.fetchall()

    news_ids = [r[0] for r in rows]
    total = len(news_ids)
    logger.info("Найдено %d новостей для перерасчета метрик...", total)

    sem = asyncio.Semaphore(4)
    success = 0
    errors = 0

    async def process_one(nid: int, idx: int):
        nonlocal success, errors
        async with sem:
            try:
                metrics = await worker.evaluate_by_id(nid)
                if metrics:
                    success += 1
                else:
                    errors += 1
            except Exception as e:
                errors += 1
                logger.error("Ошибка при перерасчете новости %d: %s", nid, e)
            if idx % 10 == 0 or idx == total:
                logger.info("Прогресс: %d / %d (успешно: %d, пропущено/ошибок: %d)", idx, total, success, errors)

    tasks = [process_one(nid, i + 1) for i, nid in enumerate(news_ids)]
    await asyncio.gather(*tasks)

    logger.info("Перерасчет завершен! Успешно: %d, Ошибок/Пропусков: %d", success, errors)

    stats = await worker.db.get_stats()
    logger.info("Обновленная статистика:")
    for k, v in stats.items():
        logger.info("  %s: %s", k, v)

    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
