"""Асинхронный клиент к публичному REST API биржи Binance."""

import logging
import re
from datetime import UTC, datetime

import httpx
from config import settings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from models import Candle

logger = logging.getLogger(__name__)

# Популярные исключения и алиасы
KNOWN_TICKER_MAP = {
    "BTC": "BTCUSDT",
    "BITCOIN": "BTCUSDT",
    "ETH": "ETHUSDT",
    "ETHEREUM": "ETHUSDT",
    "SOL": "SOLUSDT",
    "SOLANA": "SOLUSDT",
    "XRP": "XRPUSDT",
    "RIPPLE": "XRPUSDT",
    "BNB": "BNBUSDT",
    "DOGE": "DOGEUSDT",
    "ADA": "ADAUSDT",
    "CARDANO": "ADAUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "SUI": "SUIUSDT",
    "APT": "APTUSDT",
    "NEAR": "NEARUSDT",
    "DOT": "DOTUSDT",
    "XMR": "XMRUSDT",
    "MONERO": "XMRUSDT",
}

# Известные акции, индексы и не-крипто тикеры, которые не торгуются на спотовом Binance
NON_CRYPTO_BLACKLIST = {
    "TOTAL_CRYPTO",
    "GENERAL_CRYPTO",
    "DEFI",
    "STABLECOINS",
    "NFT",
    "RWA",
    "MEMES",
    "AMC",
    "ROBINHOOD",
    "HOOD",
    "ORCL",
    "ORACLE",
    "NVDA",
    "NVIDIA",
    "MU",
    "MICRON",
    "FORD",
    "F",
    "AAPL",
    "APPLE",
    "TSLA",
    "TESLA",
    "MSFT",
    "MICROSOFT",
    "GOOG",
    "GOOGL",
    "AMZN",
    "AMAZON",
    "META",
    "SPY",
    "QQQ",
    "GME",
    "COIN",
    "COINBASE",
    "MSTR",
}


class BinanceClient:
    """Клиент для получения исторических свечей и рыночных данных Binance без API-ключей."""

    def __init__(self):
        self.base_url = settings.binance_base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.http_timeout_seconds,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
        )

    async def close(self):
        """Закрывает HTTP-сессию."""
        await self.client.aclose()

    @classmethod
    def extract_tickers(cls, raw_ticker: str) -> list[str]:
        """Извлекает и разделяет тикеры, если модель вернула объединенную строку (напр. 'BTC, ETH')."""
        if not raw_ticker:
            return []
        parts = [p.strip().upper().replace("$", "") for p in re.split(r"[,/;\s]+", raw_ticker)]
        return [p for p in parts if p]

    @classmethod
    def resolve_symbol(cls, ticker: str) -> str | None:
        """Преобразует тикер актива в торговую пару Binance (например, BTC -> BTCUSDT)."""
        clean = ticker.upper().strip().replace("$", "")

        # Если строка пустая или содержит пробелы/запятые (неочищенный список)
        if not clean or " " in clean or "," in clean or "/" in clean:
            return None

        if clean in KNOWN_TICKER_MAP:
            return KNOWN_TICKER_MAP[clean]

        if clean in NON_CRYPTO_BLACKLIST:
            return None

        if clean.endswith("USDT"):
            return clean if clean[:-4].isalnum() else None

        if not clean.isalnum():
            return None

        return f"{clean}USDT"

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 1000,
    ) -> list[Candle]:
        """Запрашивает исторические свечи OHLCV с Binance."""
        url = "/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms,
            "limit": limit,
        }

        resp = await self.client.get(url, params=params)
        if resp.status_code == 400:
            # Например, символ не торгуется на Binance
            logger.warning("Символ %s не найден на Binance (HTTP 400).", symbol)
            return []

        resp.raise_for_status()
        raw_candles = resp.json()

        candles = []
        for c in raw_candles:
            candle_dt = datetime.fromtimestamp(c[0] / 1000, tz=UTC)
            candles.append(
                Candle(
                    timestamp=candle_dt,
                    open=float(c[1]),
                    high=float(c[2]),
                    low=float(c[3]),
                    close=float(c[4]),
                    volume=float(c[5]),
                )
            )
        return candles
