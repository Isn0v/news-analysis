"""Воркер для циклического сбора и разметки сентимента новостей."""

import asyncio
import logging
import signal
from typing import Dict, Any

from llm.config import settings
from llm.db import DatabaseManager
from llm.analyzer import SentimentAnalyzer

logger = logging.getLogger(__name__)


class SentimentWorker:
    """Сервис-демон, непрерывно обрабатывающий очередь новостей через внешнюю LLM."""

    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = SentimentAnalyzer()
        self.running = False
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def start(self):
        """Запуск цикла обработки новостей."""
        if not settings.llm_api_key:
            logger.warning(
                "⚠️ ВНИМАНИЕ: LLM_API_KEY не задан! "
                "Укажите ваш API-ключ в файле .env или переменной окружения (LLM_API_KEY=sk-...)."
            )

        await self.db.initialize()
        self.running = True

        stats = await self.db.get_stats()
        logger.info(
            "Старт воркера сентимента. Всего статей: %d | Обработано: %d | Ожидает: %d",
            stats["total"], stats["processed"], stats["unprocessed"]
        )

        while self.running:
            try:
                processed_count = await self._process_batch()
                if processed_count == 0:
                    # Очередь пуста — ждём новые поступления от Go-коллектора
                    await asyncio.sleep(settings.poll_interval_seconds)
            except asyncio.CancelledError:
                logger.info("Получен сигнал отмены задачи воркера.")
                break
            except Exception as e:
                logger.error("Непредвиденная ошибка в цикле воркера: %v", e, exc_info=True)
                await asyncio.sleep(5)

        await self.db.close()
        logger.info("Воркер сентимента успешно остановлен.")

    async def _process_batch(self) -> int:
        """Извлекает и параллельно обрабатывает одну пачку новостей."""
        batch = await self.db.fetch_unprocessed_batch(limit=settings.batch_size)
        if not batch:
            return 0

        logger.info("Взята пачка из %d необработанных новостей...", len(batch))

        tasks = [self._process_single_article(article) for article in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in results if not isinstance(r, Exception))
        logger.info("Пачка обработана: успешно %d / %d", success, len(batch))
        return len(batch)

    async def _process_single_article(self, article: Dict[str, Any]):
        """Обрабатывает одну статью с ограничением конкурентности через Semaphore."""
        async with self.semaphore:
            news_id = article["id"]
            title = article["title"]
            source = article["source"]

            try:
                # Анализируем через LLM
                result = await self.analyzer.analyze_article(
                    title=title,
                    content=article["content"] or article["description"],
                    source=source,
                    categories=article["categories"],
                )

                # Сохраняем в базу данных
                await self.db.save_llm_result(news_id=news_id, result=result)

                logger.info(
                    "✅ [ID %d | %s] '%s' -> Скор: %+.2f (%s) | Влияние: %d/10 | Канал: %s",
                    news_id, source, title[:40],
                    result.sentiment_score, result.sentiment_label.value,
                    result.impact_magnitude, result.transmission_channel.value
                )
                return True

            except Exception as e:
                logger.error("❌ Ошибка обработки статьи [ID %d] '%s': %s", news_id, title[:40], e)
                raise e

    def stop(self):
        """Плавная остановка воркера."""
        logger.info("Инициация плавной остановки воркера...")
        self.running = False
