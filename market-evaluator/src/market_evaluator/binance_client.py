"""Асинхронный клиент к публичному REST API биржи Binance."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from market_evaluator.config import settings
from market_evaluator.models import Candle

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

    @staticmethod
    def resolve_symbol(ticker: str) -> Optional[str]:
        """Преобразует тикер актива в торговую пару Binance (например, BTC -> BTCUSDT)."""
        clean = ticker.upper().strip()
        if clean in KNOWN_TICKER_MAP:
            return KNOWN_TICKER_MAP[clean]
        if clean.endswith("USDT"):
            return clean
        # Пропускаем макро-индексы и неконкретные сущности
        if clean in ("TOTAL_CRYPTO", "GENERAL_CRYPTO", "DEFI", "STABLECOINS", "NFT", "RWA", "MEMES"):
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
    ) -> List[Candle]:
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
            candle_dt = datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc)
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
