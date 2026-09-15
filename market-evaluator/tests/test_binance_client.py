"""Тесты для клиента Binance API."""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch
import httpx

from binance_client import BinanceClient
from models import Candle


def test_resolve_symbol():
    """Проверка резолвинга тикеров в торговые пары Binance."""
    # Известные маппинги
    assert BinanceClient.resolve_symbol("BTC") == "BTCUSDT"
    assert BinanceClient.resolve_symbol("bitcoin") == "BTCUSDT"
    assert BinanceClient.resolve_symbol("ETH") == "ETHUSDT"
    assert BinanceClient.resolve_symbol("SOLANA") == "SOLUSDT"
    assert BinanceClient.resolve_symbol("XRP") == "XRPUSDT"

    # Тикеры, уже содержащие USDT
    assert BinanceClient.resolve_symbol("BTCUSDT") == "BTCUSDT"
    assert BinanceClient.resolve_symbol("ethusdt") == "ETHUSDT"

    # Неизвестные альткоины по умолчанию дополняются USDT
    assert BinanceClient.resolve_symbol("PEPE") == "PEPEUSDT"
    assert BinanceClient.resolve_symbol("rndr") == "RNDRUSDT"

    # Макро-индексы и неконкретные сущности должны отфильтровываться (None)
    assert BinanceClient.resolve_symbol("TOTAL_CRYPTO") is None
    assert BinanceClient.resolve_symbol("DEFI") is None
    assert BinanceClient.resolve_symbol("STABLECOINS") is None
    assert BinanceClient.resolve_symbol("NFT") is None


@pytest.mark.asyncio
async def test_fetch_klines_parsing():
    """Проверка корректного парсинга сырого JSON-ответа Binance в объекты Candle."""
    client = BinanceClient()

    # Формат свечи Binance:
    # [0: open_time, 1: open, 2: high, 3: low, 4: close, 5: volume, ...]
    raw_mock_klines = [
        [
            1700000000000,  # 2023-11-14 22:13:20 UTC
            "36000.50",     # Open
            "36200.00",     # High
            "35900.10",     # Low
            "36150.00",     # Close
            "125.450",      # Volume
            1700000899999,  # Close time
            "4534567.89",   # Quote asset volume
            1500,           # Number of trades
        ]
    ]

    mock_resp = httpx.Response(
        status_code=200,
        json=raw_mock_klines,
        request=httpx.Request("GET", "https://api.binance.com/api/v3/klines"),
    )

    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        candles = await client.fetch_klines(
            symbol="BTCUSDT",
            interval="15m",
            start_time_ms=1700000000000,
            end_time_ms=1700001000000,
        )

        assert len(candles) == 1
        c = candles[0]
        assert isinstance(c, Candle)
        assert c.timestamp == datetime.fromtimestamp(1700000000, tz=timezone.utc)
        assert c.open == 36000.50
        assert c.high == 36200.00
        assert c.low == 35900.10
        assert c.close == 36150.00
        assert c.volume == 125.45

    await client.close()


@pytest.mark.asyncio
async def test_fetch_klines_not_found():
    """Проверка обработки неизвестной торговой пары (HTTP 400)."""
    client = BinanceClient()

    mock_resp = httpx.Response(
        status_code=400,
        json={"code": -1121, "msg": "Invalid symbol."},
        request=httpx.Request("GET", "https://api.binance.com/api/v3/klines"),
    )

    with patch.object(client.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        candles = await client.fetch_klines(
            symbol="NONEXISTENTUSDT",
            interval="15m",
            start_time_ms=1700000000000,
            end_time_ms=1700001000000,
        )

        # Должен вернуть пустой список без падения с исключением
        assert candles == []

    await client.close()
