"""Тест фильтрации спекулятивных новостей и автономного определения валют/категорий."""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "llm"))

from db import DatabaseManager as LLMDb
from analyzer import SentimentAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 18643: Спекуляция (Bloomberg strategist warns of crash)
# 17447: Твердый факт (Hackers mint fake BTC, bridge exploit)
TEST_NEWS_IDS = [18643, 17447]

async def main():
    llm_db = LLMDb()
    await llm_db.initialize()
    analyzer = SentimentAnalyzer()

    for news_id in TEST_NEWS_IDS:
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
        print("\n" + "=" * 80)
        print(f"📰 ID {news_id}: {title}")
        print(f"   RSS категории: {categories}")
        print("=" * 80)

        result = await analyzer.analyze_article(
            title=title,
            content=content or description,
            source=source,
            categories=categories or [],
        )
        await llm_db.save_llm_result(news_id=news_id, result=result)

        print(f"🤖 ВЕРДИКТ LLM:")
        print(f"   Спекулятивная:        {'🚨 ДА (Шум / Частное мнение)' if result.is_speculative else '🛡 НЕТ (Твердый факт / Катализатор)'}")
        print(f"   Причина:              {result.speculation_reason}")
        print(f"   Выявленные валюты:    {result.detected_currencies}")
        print(f"   Выявленные категории: {result.detected_categories}")
        print(f"   Сентимент:            {result.sentiment_label.value} ({result.sentiment_score:+0.2f})")

        print("\n📈 ШАГ MARKET-EVALUATOR:")
        cmd = ["uv", "run", "python", "main.py", "--news-id", str(news_id)]
        res = subprocess.run(cmd, cwd=str(ROOT_DIR / "market-evaluator"), capture_output=True, text=True)
        print(res.stdout)

    await llm_db.close()

if __name__ == "__main__":
    asyncio.run(main())
