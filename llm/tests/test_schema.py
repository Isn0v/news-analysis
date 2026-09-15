"""Тесты валидации Pydantic-схем анализа сентимента."""

import pytest
from pydantic import ValidationError

from schema import (
    SentimentAnalysisResult,
    SentimentLabel,
    InformationType,
    MarketSurprise,
    TransmissionChannel,
    TimeHorizon,
    AssetImpact,
)


def test_valid_sentiment_analysis_result():
    """Проверка успешной валидации корректного результата анализа."""
    data = {
        "sentiment_score": 0.75,
        "sentiment_label": "bullish",
        "confidence": 0.9,
        "impact_magnitude": 8,
        "time_horizon": "immediate_1h_4h",
        "information_type": "hard_fact",
        "market_surprise": "better_than_expected",
        "transmission_channel": "regulatory",
        "affected_assets": [
            {"ticker": "BTC", "sentiment": 0.8, "reason": "Приток ETF"},
            {"ticker": "ETH", "sentiment": 0.6, "reason": "Общий позитив"},
        ],
        "key_takeaways": ["SEC одобрила ETF", "Ожидаются притоки от фондов"],
        "target_horizon_hours": 4,
        "is_mean_reverting": False,
        "is_speculative": False,
        "speculation_reason": "Официальное решение регулятора США",
        "detected_currencies": ["BTC", "ETH"],
        "detected_categories": ["Regulation", "ETF"],
        "reasoning": "Одобрение ETF устраняет регуляторный дисконт и открывает доступ пенсионным фондам.",
    }

    result = SentimentAnalysisResult.model_validate(data)
    assert result.sentiment_score == 0.75
    assert result.sentiment_label == SentimentLabel.BULLISH
    assert result.confidence == 0.9
    assert result.impact_magnitude == 8
    assert result.is_speculative is False
    assert result.detected_currencies == ["BTC", "ETH"]
    assert len(result.affected_assets) == 2


def test_sentiment_score_bounds():
    """Проверка ограничений диапазона sentiment_score [-1.0, 1.0]."""
    valid_data = {
        "sentiment_label": "bullish",
        "confidence": 0.8,
        "impact_magnitude": 5,
        "time_horizon": "immediate_1h_4h",
        "information_type": "hard_fact",
        "market_surprise": "in_line",
        "transmission_channel": "general_crypto",
        "reasoning": "тест",
    }

    # Значение > 1.0 должно вызывать ошибку валидации
    with pytest.raises(ValidationError):
        SentimentAnalysisResult.model_validate({**valid_data, "sentiment_score": 1.5})

    # Значение < -1.0 должно вызывать ошибку валидации
    with pytest.raises(ValidationError):
        SentimentAnalysisResult.model_validate({**valid_data, "sentiment_score": -1.2})


def test_impact_magnitude_bounds():
    """Проверка ограничений силы влияния impact_magnitude [1, 10]."""
    valid_data = {
        "sentiment_score": 0.0,
        "sentiment_label": "neutral",
        "confidence": 0.5,
        "time_horizon": "immediate_1h_4h",
        "information_type": "opinion_analysis",
        "market_surprise": "not_applicable",
        "transmission_channel": "none",
        "reasoning": "тест",
    }

    with pytest.raises(ValidationError):
        SentimentAnalysisResult.model_validate({**valid_data, "impact_magnitude": 0})

    with pytest.raises(ValidationError):
        SentimentAnalysisResult.model_validate({**valid_data, "impact_magnitude": 11})


def test_speculative_defaults():
    """Проверка дефолтных значений флагов спекулятивности и списков."""
    valid_data = {
        "sentiment_score": -0.4,
        "sentiment_label": "bearish",
        "confidence": 0.7,
        "impact_magnitude": 4,
        "time_horizon": "short_term_1d_3d",
        "information_type": "rumor_leak",
        "market_surprise": "worse_than_expected",
        "transmission_channel": "defi_tech_exploit",
        "reasoning": "Слух о взломе",
    }

    result = SentimentAnalysisResult.model_validate(valid_data)
    assert result.is_speculative is False  # дефолт
    assert result.speculation_reason == ""
    assert result.detected_currencies == []
    assert result.detected_categories == []
