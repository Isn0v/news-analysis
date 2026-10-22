"""Воркер для циклической или пакетной оценки рыночного влияния новостей."""

import asyncio
import logging
from datetime import UTC
from typing import Any

import httpx
import psycopg
from binance_client import BinanceClient
from config import settings
from db import DatabaseManager
from engine import EventStudyEngine

from models import EventStudyMetrics

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

    async def evaluate_article(self, article: dict[str, Any]) -> list[EventStudyMetrics]:
        """Оценивает влияние одной статьи на все затронутые активы."""
        news_id = article["news_id"]
        title = article.get("title", "")
        t0_timestamp = article["timestamp_utc"]
        llm_result = article.get("llm_result") or {}

        logger.debug("Оценка новости [ID %d]: %s", news_id, title)

        if not t0_timestamp:
            logger.warning("У статьи [ID %d] нет timestamp_utc", news_id)
            return []

        # Обеспечиваем timezone-aware UTC
        if t0_timestamp.tzinfo is None:
            t0_timestamp = t0_timestamp.replace(tzinfo=UTC)

        # Классификация спекулятивности
        is_speculative = bool(llm_result.get("is_speculative", False))
        spec_reason = llm_result.get("speculation_reason", "")
        if is_speculative and spec_reason:
            logger.debug("Причина спекулятивности [ID %d]: %s", news_id, spec_reason)

        affected_assets = llm_result.get("affected_assets") or []
        # Fallback: если affected_assets пуст, пробуем извлечь из detected_currencies
        if not affected_assets:
            detected_currencies = llm_result.get("detected_currencies") or []
            sentiment_score = float(llm_result.get("sentiment_score", 0.0))
            affected_assets = [
                {
                    "ticker": cur.strip().upper(),
                    "sentiment": sentiment_score,
                    "reason": "Extracted from detected_currencies",
                }
                for cur in detected_currencies
                if cur.strip()
            ]

        sentiment_label = llm_result.get("sentiment_label", "neutral")
        sentiment_score = float(llm_result.get("sentiment_score", 0.0))
        impact_magnitude = int(llm_result.get("impact_magnitude", 5))
        target_horizon_hours = int(llm_result.get("target_horizon_hours", 4))
        is_mean_reverting = bool(llm_result.get("is_mean_reverting", False))
        llm_model = article.get("llm_model") or llm_result.get("model_name") or "unknown"

        if not affected_assets:
            logger.debug("У статьи [ID %d] нет затронутых активов", news_id)
            return []

        results = []
        t0_ms = int(t0_timestamp.timestamp() * 1000)
        start_ms = t0_ms - (settings.pre_window_hours * 3600 * 1000)
        post_hours = max(settings.post_window_hours, target_horizon_hours + 2)
        end_ms = t0_ms + (post_hours * 3600 * 1000)

        for asset in affected_assets:
            raw_ticker = asset.get("ticker", "").strip()
            tickers = BinanceClient.extract_tickers(raw_ticker)
            if not tickers:
                continue

            for ticker in tickers:
                symbol = BinanceClient.resolve_symbol(ticker)
                if not symbol:
                    logger.debug("Тикер '%s' пропущен (не является криптовалютной парой Binance)", ticker)
                    continue

                try:
                    # Получаем свечи с Binance
                    candles = await self.binance.fetch_klines(
                        symbol=symbol,
                        interval=settings.candle_interval,
                        start_time_ms=start_ms,
                        end_time_ms=end_ms,
                    )
                except (httpx.HTTPError, ValueError, KeyError) as e:
                    logger.warning("Ошибка запроса свечей Binance для %s (новость ID %d): %s", symbol, news_id, e)
                    continue

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
                    is_speculative=is_speculative,
                    llm_model=llm_model,
                )

                if metrics:
                    await self.db.save_market_impact(news_id=news_id, metrics=metrics)
                    results.append(metrics)
                    type_tag = "🚨 СПЕКУЛЯЦИЯ" if metrics.is_speculative else "🛡 ФАКТ"
                    logger.info(
                        "📊 [ID %d | %s | %s] P0: $%s | VolSurge: x%0.2f | Импульс: %s | Горизонт %dч: %s",
                        news_id,
                        symbol,
                        type_tag,
                        metrics.p0_price,
                        metrics.volume_surge_ratio,
                        "✅" if metrics.is_impulse_confirmed else "❌",
                        metrics.target_horizon_hours,
                        "✅" if metrics.is_target_horizon_aligned else "❌",
                    )

        # Всегда помечаем новость как оцененную, чтобы исключить зацикливание воркера
        await self.db.mark_news_evaluated(news_id)
        if not results:
            logger.info(
                "ℹ️ [ID %d] Оценка завершена без метрик (активы не торгуются на Binance или нет свечей). Новость помечена обработанной.",
                news_id,
            )

        return results

    async def evaluate_by_id(self, news_id: int) -> list[EventStudyMetrics]:
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
            except (psycopg.Error, httpx.HTTPError) as infra_err:
                logger.error("Инфраструктурная ошибка в цикле market-evaluator (DB/Binance): %s. Пауза 10с...", infra_err)
                await asyncio.sleep(10)

        logger.info("Демон market-evaluator остановлен.")

    def stop(self):
        """Остановка демона."""
        self.running = False
