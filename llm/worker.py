"""Воркер для циклического сбора и разметки сентимента новостей."""

import asyncio
import logging
from typing import Any

import psycopg
from analyzer import SentimentAnalyzer
from config import settings
from db import DatabaseManager
from openai import APIConnectionError, APIError, RateLimitError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class SentimentWorker:
    """Сервис-демон, непрерывно обрабатывающий очередь новостей через LLM."""

    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = SentimentAnalyzer()
        self.running = False
        self.worker_id = settings.worker_id
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

    async def start(self):
        """Запуск основного цикла обработки новостей."""
        await self.db.initialize()
        self.running = True

        stats = await self.db.get_stats()
        logger.info(
            "Старт воркера сентимента [%s]. Всего статей: %d | Обработано: %d | Ожидает: %d",
            self.worker_id,
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
                logger.info("Получен сигнал отмены задачи воркера [%s].", self.worker_id)
                break
            except (psycopg.Error, APIConnectionError, RateLimitError) as e:
                logger.error(
                    "[%s] Инфраструктурная ошибка в цикле воркера (DB/LLM): %s. Повтор через %dс...",
                    self.worker_id,
                    e,
                    settings.error_retry_delay_seconds,
                )
                await asyncio.sleep(settings.error_retry_delay_seconds)

        await self.db.close()
        logger.info("Воркер сентимента [%s] успешно остановлен.", self.worker_id)

    async def _process_batch(self) -> int:
        """Извлекает и параллельно обрабатывает одну пачку новостей (атомарный захват SKIP LOCKED)."""
        batch = await self.db.fetch_unprocessed_batch(
            limit=settings.batch_size,
            worker_id=self.worker_id,
            lock_timeout_minutes=settings.lock_timeout_minutes,
        )
        if not batch:
            return 0

        logger.info("[%s] Взята пачка из %d необработанных новостей...", self.worker_id, len(batch))

        tasks = [self._process_single_article(article) for article in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in results if r is True)
        logger.info("[%s] Пачка обработана: успешно %d / %d", self.worker_id, success, len(batch))

        # При инфраструктурных ошибках LLM делаем паузу во избежание быстрого спама в цикле
        infra_errors = [r for r in results if isinstance(r, (APIConnectionError, RateLimitError))]
        if infra_errors:
            logger.warning(
                "[%s] Обнаружены инфраструктурные ошибки LLM. Пауза %dс перед следующей попыткой...",
                self.worker_id,
                settings.error_retry_delay_seconds,
            )
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

                await self.db.save_llm_result(news_id=news_id, result=result, model=self.analyzer.model)

                logger.info(
                    "✅ [%s | ID %d | %s] '%s' -> Скор: %+.2f (%s) | Горизонт: %dч (Откат: %s) | Канал: %s",
                    self.worker_id,
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

            except (APIConnectionError, RateLimitError):
                logger.error(
                    "❌ [%s] Инфраструктурная ошибка LLM при анализе [ID %d] '%s'",
                    self.worker_id,
                    news_id,
                    title[:40],
                    exc_info=True,
                )
                # Немедленно снимаем блокировку, чтобы другой живой воркер мог взять статью без ожидания таймаута
                await self.db.release_locks([news_id])
                raise

            except (APIError, ValidationError, ValueError, KeyError) as e:
                logger.error("❌ [%s] Ошибка обработки статьи [ID %d] '%s': %s", self.worker_id, news_id, title[:40], e)
                try:
                    await self.db.save_llm_error(news_id=news_id, error_message=str(e), model=self.analyzer.model)
                    logger.warning(
                        "Статья [ID %d] помечена как обработанная с записью ошибки во избежание зацикливания.", news_id
                    )
                except psycopg.Error as db_err:
                    logger.error("Не удалось сохранить статус ошибки для статьи [ID %d]: %s", news_id, db_err)
                return False

    def stop(self):
        """Плавная остановка воркера."""
        logger.info("Инициация плавной остановки воркера...")
        self.running = False
