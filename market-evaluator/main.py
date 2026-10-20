"""Точка входа и CLI-интерфейс для сервиса market-evaluator."""

import argparse
import asyncio
import contextlib
import logging
import signal
import sys

from config import settings
from worker import MarketEvaluationWorker


def setup_logging():
    """Настройка логирования."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


async def async_main():
    parser = argparse.ArgumentParser(description="Market Evaluator & Event Study CLI")
    parser.add_argument("--news-id", type=int, help="Оценить конкретную новость по ID")
    parser.add_argument("--batch", action="store_true", help="Оценить все доступные статьи пачкой")
    parser.add_argument("--limit", type=int, default=100, help="Лимит статей для пакетного режима")
    parser.add_argument("--stats", action="store_true", help="Показать статистику точности прогнозов")
    parser.add_argument("--daemon", action="store_true", help="Запустить в режиме непрерывного демона")

    args = parser.parse_args()
    setup_logging()

    worker = MarketEvaluationWorker()
    await worker.initialize()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop)

    try:
        if args.stats:
            stats = await worker.db.get_stats()
            print("\n" + "=" * 60)
            print("📊 СТАТИСТИКА ТОЧНОСТИ И РЫНОЧНОГО ВЛИЯНИЯ:")
            print("=" * 60)
            for k, v in stats.items():
                print(f"  {k:25}: {v}")
            print("=" * 60 + "\n")

        elif args.news_id:
            print(f"\n🔍 Анализ рыночной реакции для новости ID {args.news_id}...")
            article = await worker.db.fetch_news_by_id(args.news_id)
            if not article:
                print(f"❌ Новость с ID {args.news_id} не найдена в базе данных.")
            else:
                llm_res = article.get("llm_result") or {}
                is_spec = llm_res.get("is_speculative", False)
                spec_reason = llm_res.get("speculation_reason", "")
                if is_spec:
                    print(f"🚨 Тип события: СПЕКУЛЯТИВНЫЙ ШУМ (Причина: {spec_reason})")
                else:
                    print(f"🛡 Тип события: ТВЕРДЫЙ ФАКТ / КАТАЛИЗАТОР (Причина: {spec_reason})")

                metrics_list = await worker.evaluate_article(article)
                if not metrics_list:
                    print("❌ Не удалось рассчитать метрики (проверьте наличие тикера или историю свечей).")
                else:
                    for m in metrics_list:
                        print("\n" + "-" * 60)
                        print(f"АКТИВ: {m.symbol} ({m.ticker})")
                        print(f"Класс события:         {'🚨 Спекуляция' if m.is_speculative else '🛡 Твердый факт'}")
                        print(f"Время события (t0):    {m.t0_timestamp} UTC")
                        print(f"Базовая цена (P0):     ${m.p0_price:,.4f}")
                        print(f"Pre-News Drift (-4ч):   {m.pre_drift_pct:+.2f}%")
                        print(f"Всплеск объема на t0:  x{m.volume_surge_ratio:.2f}")
                        print(
                            f"Доходность +15м:       {f'{m.return_15m_pct:+.2f}%' if m.return_15m_pct is not None else 'N/A'}"
                        )
                        print(
                            f"Доходность +1ч:        {f'{m.return_1h_pct:+.2f}%' if m.return_1h_pct is not None else 'N/A'}"
                        )
                        print(
                            f"Доходность +4ч:        {f'{m.return_4h_pct:+.2f}%' if m.return_4h_pct is not None else 'N/A'}"
                        )
                        print(
                            f"Доходность +24ч:       {f'{m.return_24h_pct:+.2f}%' if m.return_24h_pct is not None else 'N/A'}"
                        )
                        print(f"Макс. взлет (Run-up):  {m.max_runup_pct:+.2f}%")
                        print(
                            f"Оценка LLM:            {m.sentiment_label} (скор {m.sentiment_score:+0.2f}, импакт {m.impact_magnitude}/10)"
                        )
                        print(
                            f"Целевой горизонт LLM:  {m.target_horizon_hours} ч (Откат: {'Да' if m.is_mean_reverting_expected else 'Нет'})"
                        )
                        print(
                            f"Первичный импульс (2ч): {'✅ Сработал' if m.is_impulse_confirmed else '❌ Не сработал'}"
                        )
                        target_status = (
                            "✅ Подтвержден"
                            if m.is_target_horizon_aligned
                            else ("❌ Не подтвержден" if m.is_target_horizon_aligned is False else "⏳ В ожидании")
                        )
                        print(f"Целевой горизонт ({m.target_horizon_hours}ч): {target_status}")
                        print(
                            f"Сетка фикс-горизонтов: 1ч: {'✅' if m.is_aligned_1h else '❌'} | 4ч: {'✅' if m.is_aligned_4h else '❌'}"
                        )
                        print("-" * 60)

        elif args.batch:
            print(f"🚀 Запуск пакетной оценки до {args.limit} новостей...")
            count = await worker.evaluate_batch_all(limit=args.limit)
            print(f"✅ Успешно оценено новостей: {count}")

        else:
            # По умолчанию запускаем демон
            await worker.start()

    finally:
        await worker.close()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
