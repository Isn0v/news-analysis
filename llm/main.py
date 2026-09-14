"""Точка входа для запуска сервиса анализа сентимента."""

import asyncio
import logging
import signal
import sys

from config import settings
from worker import SentimentWorker


def setup_logging():
    """Настройка структурированного логирования."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def main():
    setup_logging()
    worker = SentimentWorker()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Регистрация обработчиков сигналов остановки
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, worker.stop)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(worker.start())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
