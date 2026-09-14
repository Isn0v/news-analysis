"""Проверка отработанных новостей возрастом > 48 часов, где горизонт 24ч/48ч уже наступил."""

import asyncio
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "llm"))
from db import DatabaseManager as LLMDb
from analyzer import SentimentAnalyzer

sys.path.insert(0, str(ROOT_DIR / "market-evaluator"))
from worker import MarketEvaluationWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

TEST_IDS = [431, 180]  # XRP ETF Filing, XRP 1B dump

async def main():
    llm_db = LLMDb()
    await llm_db.initialize()
    analyzer = SentimentAnalyzer()
    worker = MarketEvaluationWorker()
    await worker.initialize()

    for news_id in TEST_IDS:
        async with llm_db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT title, content, description, source, categories FROM raw_news WHERE id = %s;",
                    (news_id,)
                )
                row = await cur.fetchone()
        if not row:
            continue
        title, content, description, source, categories = row
        print(f"\n🧠 Анализ новости ID {news_id}: {title}...")
        result = await analyzer.analyze_article(
            title=title,
            content=content or description,
            source=source,
            categories=categories or []
        )
        await llm_db.save_llm_result(news_id=news_id, result=result)
        print(f"   -> Сентимент: {result.sentiment_label.value} ({result.sentiment_score:+0.2f}) | Горизонт: {result.target_horizon_hours}ч | Откат: {result.is_mean_reverting}")

        metrics = await worker.evaluate_by_id(news_id)
        for m in metrics:
            print(f"   -> {m.symbol} P0: ${m.p0_price:,.4f}")
            print(f"      Импульс (2ч): {'✅' if m.is_impulse_confirmed else '❌'} | Всплеск объема: x{m.volume_surge_ratio:.2f}")
            print(f"      Ret 1h: {m.return_1h_pct:+0.2f}% | Ret 4h: {m.return_4h_pct:+0.2f}% | Ret 24h: {m.return_24h_pct:+0.2f}%")
            print(f"      Целевой горизонт ({m.target_horizon_hours}ч): {'✅' if m.is_target_horizon_aligned else '❌'}")

    await worker.close()
    await llm_db.close()

if __name__ == "__main__":
    asyncio.run(main())
