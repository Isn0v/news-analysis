"""Воркер для циклического сбора и разметки сентимента новостей."""

import asyncio
import logging
from typing import Any

from openai import APIConnectionError, RateLimitError

from analyzer import SentimentAnalyzer
from config import settings
from db import DatabaseManager

logger = logging.getLogger(__name__)


class SentimentWorker:
    """Сервис-демон, непрерывно обрабатывающий очередь новостей через LLM."""

    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = SentimentAnalyzer()
        self.running = False
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def start(self):
        """Запуск основного цикла обработки новостей."""
        await self.db.initialize()
        self.running = True

        stats = await self.db.get_stats()
        logger.info(
            "Старт воркера сентимента. Всего статей: %d | Обработано: %d | Ожидает: %d",
            stats["total"],
            stats["processed"],
            stats["unprocessed"],
        )

        while self.running:
            try:
                processed_count = await self._process_batch()
                if processed_count == 0:
                    # Очередь пуста — ждём новые поступления от сборщика
                    await asyncio.sleep(settings.poll_interval_seconds)
            except asyncio.CancelledError:
                logger.info("Получен сигнал отмены задачи воркера.")
                break
            except Exception as e:
                logger.error("Ошибка в цикле воркера: %s. Повтор через %dс...", e, settings.error_retry_delay_seconds, exc_info=True)
                await asyncio.sleep(settings.error_retry_delay_seconds)

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

        success = sum(1 for r in results if r is True)
        logger.info("Пачка обработана: успешно %d / %d", success, len(batch))

        # При инфраструктурных ошибках LLM делаем паузу во избежание быстрого спама в цикле
        infra_errors = [r for r in results if isinstance(r, (APIConnectionError, RateLimitError))]
        if infra_errors:
            logger.warning("Обнаружены инфраструктурные ошибки LLM. Пауза %dс перед следующей попыткой...", settings.error_retry_delay_seconds)
            await asyncio.sleep(settings.error_retry_delay_seconds)

        return len(batch)

    async def _process_single_article(self, article: dict[str, Any]):
        """Обрабатывает одну статью с ограничением конкурентности через Semaphore."""
        async with self.semaphore:
            news_id = article["id"]
            title = article["title"]
            source = article["source"]

            try:
                result = await self.analyzer.analyze_article(
                    title=title,
                    content=article["content"] or article["description"],
                    source=source,
                    categories=article["categories"],
                )

                await self.db.save_llm_result(news_id=news_id, result=result)

                logger.info(
                    "✅ [ID %d | %s] '%s' -> Скор: %+.2f (%s) | Горизонт: %dч (Откат: %s) | Канал: %s",
                    news_id,
                    source,
                    title[:35],
                    result.sentiment_score,
                    result.sentiment_label.value,
                    result.target_horizon_hours,
                    "Да" if result.is_mean_reverting else "Нет",
                    result.transmission_channel.value,
                )
                return True

            except (APIConnectionError, RateLimitError) as infra_err:
                logger.error("❌ Инфраструктурная ошибка LLM при анализе [ID %d] '%s': %s", news_id, title[:40], infra_err)
                raise infra_err

            except Exception as e:
                logger.error("❌ Ошибка обработки статьи [ID %d] '%s': %s", news_id, title[:40], e)
                try:
                    await self.db.save_llm_error(news_id=news_id, error_message=str(e))
                    logger.warning("Статья [ID %d] помечена как обработанная с записью ошибки во избежание зацикливания.", news_id)
                except Exception as db_err:
                    logger.error("Не удалось сохранить статус ошибки для статьи [ID %d]: %s", news_id, db_err)
                return False

    def stop(self):
        """Плавная остановка воркера."""
        logger.info("Инициация плавной остановки воркера...")
        self.running = False
