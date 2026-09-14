"""Скрипт для проверки гипотезы прогнозирования горизонта влияния на реальных новостях."""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "llm" / "src"))
sys.path.insert(0, str(ROOT_DIR / "market-evaluator" / "src"))

from llm.db import DatabaseManager as LLMDb
from llm.analyzer import SentimentAnalyzer
from market_evaluator.db import DatabaseManager as EvalDb
from market_evaluator.worker import MarketEvaluationWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

TARGET_NEWS_IDS = [
    18580,  # Bitcoin Faces 87% Fed Hike Odds (Macro/Fed)
    18643,  # New Bitcoin Crash Ahead? Bloomberg Strategist (FUD/Opinion)
    18216,  # How XRP Is Filling the Cash Gap: South Korea (XRP Adoption)
    17719,  # Whale Moves 1,260 BTC (Onchain Whale)
    17447,  # Hackers mint trillions in fake Bitcoin bridge (Security/Exploit)
    13126,  # Solana Mobile Suspends Email Account (Security/Solana)
    14806,  # XRP to Outperform Bitcoin? Analyst Maps 306% (Bullish Opinion)
    14858,  # Critical Bitcoin Lightning bugs exposed (Tech Vulnerability)
]


async def run_experiment():
    llm_db = LLMDb()
    await llm_db.initialize()
    analyzer = SentimentAnalyzer()

    eval_worker = MarketEvaluationWorker()
    await eval_worker.initialize()

    print("=" * 80)
    print(f"🔬 ЗАПУСК ЭКСПЕРИМЕНТА: ТЕСТИРОВАНИЕ ГИПОТЕЗЫ НА {len(TARGET_NEWS_IDS)} ОТРАБОТАННЫХ НОВОСТЯХ")
    print("=" * 80)

    # 1. Шаг инференса через DeepSeek R1
    for news_id in TARGET_NEWS_IDS:
        async with llm_db.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT title, content, description, source, categories, timestamp_utc FROM raw_news WHERE id = %s;",
                    (news_id,)
                )
                row = await cur.fetchone()

        if not row:
            continue

        title, content, description, source, categories, t0 = row
        print(f"\n[1/2] 🧠 Инференс LLM для ID {news_id}: {title[:55]}...")
        
        result = await analyzer.analyze_article(
            title=title,
            content=content or description,
            source=source,
            categories=categories or [],
        )

        await llm_db.save_llm_result(news_id=news_id, result=result)
        print(
            f"      -> Сентимент: {result.sentiment_label.value} ({result.sentiment_score:+0.2f}) | "
            f"Горизонт LLM: {result.target_horizon_hours}ч | Откат: {result.is_mean_reverting} | Импакт: {result.impact_magnitude}/10"
        )

        # 2. Шаг оценки рыночного влияния через Binance
        print(f"[2/2] 📈 Сбор рыночных данных и расчет Event Study...")
        metrics = await eval_worker.evaluate_by_id(news_id)
        for m in metrics:
            print(
                f"      -> {m.symbol}: P0=${m.p0_price:,.2f} | Импульс (2ч): {'✅' if m.is_impulse_confirmed else '❌'} | "
                f"Целевой горизонт ({m.target_horizon_hours}ч): {'✅' if m.is_target_horizon_aligned else '❌'} | "
                f"Ret 1h: {f'{m.return_1h_pct:+0.2f}%' if m.return_1h_pct else 'N/A'} | "
                f"Ret 4h: {f'{m.return_4h_pct:+0.2f}%' if m.return_4h_pct else 'N/A'}"
            )

    # 3. Итоговая аналитика
    stats = await eval_worker.db.get_stats()
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЙ ОТЧЕТ ПРОВЕРКИ ГИПОТЕЗЫ:")
    print("=" * 80)
    for k, v in stats.items():
        print(f"  {k:30}: {v}")
    print("=" * 80)

    await eval_worker.close()
    await llm_db.close()


if __name__ == "__main__":
    asyncio.run(run_experiment())
