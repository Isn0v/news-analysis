"""Воркер для циклической или пакетной оценки рыночного влияния новостей."""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from market_evaluator.config import settings
from market_evaluator.db import DatabaseManager
from market_evaluator.binance_client import BinanceClient
from market_evaluator.engine import EventStudyEngine
from market_evaluator.models import EventStudyMetrics

logger = logging.getLogger(__name__)


class MarketEvaluationWorker:
    """Оркестратор оценки рыночной реакции на события."""

    def __init__(self):
        self.db = DatabaseManager()
        self.binance = BinanceClient()
        self.running = False

    async def initialize(self):
        """Инициализация ресурсов."""
        await self.db.initialize()

    async def close(self):
        """Освобождение ресурсов."""
        await self.binance.close()
        await self.db.close()

    async def evaluate_article(self, article: Dict[str, Any]) -> List[EventStudyMetrics]:
        """Оценивает влияние одной статьи на все затронутые активы."""
        news_id = article["news_id"]
        title = article["title"]
        t0_timestamp = article["timestamp_utc"]
        llm_result = article.get("llm_result") or {}

        if not t0_timestamp:
            logger.warning("У статьи [ID %d] нет timestamp_utc", news_id)
            return []

        # Обеспечиваем timezone-aware UTC
        if t0_timestamp.tzinfo is None:
            t0_timestamp = t0_timestamp.replace(tzinfo=timezone.utc)

        affected_assets = llm_result.get("affected_assets") or []
        sentiment_label = llm_result.get("sentiment_label", "neutral")
        sentiment_score = float(llm_result.get("sentiment_score", 0.0))
        impact_magnitude = int(llm_result.get("impact_magnitude", 5))
        target_horizon_hours = int(llm_result.get("target_horizon_hours", 4))
        is_mean_reverting = bool(llm_result.get("is_mean_reverting", False))

        if not affected_assets:
            logger.debug("У статьи [ID %d] нет затронутых активов", news_id)
            return []

        results = []
        t0_ms = int(t0_timestamp.timestamp() * 1000)
        start_ms = t0_ms - (settings.pre_window_hours * 3600 * 1000)
        post_hours = max(settings.post_window_hours, target_horizon_hours + 2)
        end_ms = t0_ms + (post_hours * 3600 * 1000)

        for asset in affected_assets:
            ticker = asset.get("ticker", "").strip().upper()
            if not ticker:
                continue

            symbol = BinanceClient.resolve_symbol(ticker)
            if not symbol:
                logger.debug("Тикер '%s' пропущен (не является торговой парой Binance)", ticker)
                continue

            # Получаем свечи с Binance
            candles = await self.binance.fetch_klines(
                symbol=symbol,
                interval=settings.candle_interval,
                start_time_ms=start_ms,
                end_time_ms=end_ms,
            )

            if not candles:
                logger.warning("Не удалось получить свечи для %s (новость ID %d)", symbol, news_id)
                continue

            # Расчет метрик с учетом горизонта
            metrics = EventStudyEngine.compute(
                candles=candles,
                t0_timestamp=t0_timestamp,
                ticker=ticker,
                symbol=symbol,
                sentiment_label=sentiment_label,
                sentiment_score=sentiment_score,
                impact_magnitude=impact_magnitude,
                target_horizon_hours=target_horizon_hours,
                is_mean_reverting=is_mean_reverting,
            )

            if metrics:
                await self.db.save_market_impact(news_id=news_id, metrics=metrics)
                results.append(metrics)
                logger.info(
                    "📊 [ID %d | %s] P0: $%s | VolSurge: x%0.2f | Импульс: %s | Горизонт %dч: %s",
                    news_id,
                    symbol,
                    metrics.p0_price,
                    metrics.volume_surge_ratio,
                    "✅" if metrics.is_impulse_confirmed else "❌",
                    metrics.target_horizon_hours,
                    "✅" if metrics.is_target_horizon_aligned else "❌",
                )

        return results

    async def evaluate_by_id(self, news_id: int) -> List[EventStudyMetrics]:
        """Оценивает конкретную новость по ее ID."""
        article = await self.db.fetch_news_by_id(news_id)
        if not article:
            logger.error("Новость с ID %d не найдена в базе", news_id)
            return []
        return await self.evaluate_article(article)

    async def evaluate_batch_all(self, limit: int = 100) -> int:
        """Пакетная оценка всех доступных новостей."""
        total_evaluated = 0
        while True:
            batch = await self.db.fetch_unevaluated_news(limit=settings.batch_size)
            if not batch:
                break

            for article in batch:
                res = await self.evaluate_article(article)
                if res:
                    total_evaluated += 1
                # Небольшая пауза для соблюдения лимитов публичного API Binance
                await asyncio.sleep(0.3)

            if total_evaluated >= limit:
                break

        return total_evaluated

    async def start(self):
        """Запуск воркера в режиме постоянного демона."""
        self.running = True
        logger.info("Запуск демона market-evaluator...")

        while self.running:
            try:
                batch = await self.db.fetch_unevaluated_news(limit=settings.batch_size)
                if batch:
                    logger.info("Найдено %d новостей для оценки рыночного влияния...", len(batch))
                    for article in batch:
                        if not self.running:
                            break
                        await self.evaluate_article(article)
                        await asyncio.sleep(0.5)
                else:
                    await asyncio.sleep(settings.poll_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Ошибка в цикле market-evaluator: %s", e, exc_info=True)
                await asyncio.sleep(10)

        logger.info("Демон market-evaluator остановлен.")

    def stop(self):
        """Остановка демона."""
        self.running = False
