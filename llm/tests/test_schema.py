"""Тесты валидации Pydantic-схем анализа сентимента."""

import pytest
from pydantic import ValidationError
from schema import (
    SentimentAnalysisResult,
    SentimentLabel,
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


def test_align_sentiment_sign_and_label():
    """Проверка автоматической синхронизации знака sentiment_score и sentiment_label."""
    base_data = {
        "confidence": 0.8,
        "impact_magnitude": 5,
        "time_horizon": "immediate_1h_4h",
        "information_type": "hard_fact",
        "market_surprise": "in_line",
        "transmission_channel": "general_crypto",
        "reasoning": "Тест синхронизации сентимента",
    }

    # 1. Bearish с положительным score -> score инвертируется в отрицательный
    res_bearish = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "bearish", "sentiment_score": 0.25}
    )
    assert res_bearish.sentiment_score == -0.25
    assert res_bearish.sentiment_label == SentimentLabel.BEARISH

    # 2. Bullish с отрицательным score -> score инвертируется в положительный
    res_bullish = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "bullish", "sentiment_score": -0.35}
    )
    assert res_bullish.sentiment_score == 0.35
    assert res_bullish.sentiment_label == SentimentLabel.BULLISH

    # 3. Bearish с нулевым score -> становится -0.15
    res_bearish_zero = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "bearish", "sentiment_score": 0.0}
    )
    assert res_bearish_zero.sentiment_score == -0.15
    assert res_bearish_zero.sentiment_label == SentimentLabel.BEARISH

    # 4. Bullish с нулевым score -> становится 0.15
    res_bullish_zero = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "bullish", "sentiment_score": 0.0}
    )
    assert res_bullish_zero.sentiment_score == 0.15
    assert res_bullish_zero.sentiment_label == SentimentLabel.BULLISH

    # 5. Neutral со значимым положительным score (>= 0.10) -> label становится bullish
    res_neutral_pos = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "neutral", "sentiment_score": 0.40}
    )
    assert res_neutral_pos.sentiment_score == 0.40
    assert res_neutral_pos.sentiment_label == SentimentLabel.BULLISH

    # 6. Neutral со значимым отрицательным score (<= -0.10) -> label становится bearish
    res_neutral_neg = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "neutral", "sentiment_score": -0.40}
    )
    assert res_neutral_neg.sentiment_score == -0.40
    assert res_neutral_neg.sentiment_label == SentimentLabel.BEARISH

    # 7. Истинный Neutral (-0.10 < score < 0.10) -> остается neutral
    res_neutral_ok = SentimentAnalysisResult.model_validate(
        {**base_data, "sentiment_label": "neutral", "sentiment_score": 0.05}
    )
    assert res_neutral_ok.sentiment_score == 0.05
    assert res_neutral_ok.sentiment_label == SentimentLabel.NEUTRAL


def test_moex_result_validation():
    """Проверка валидации результата для рынка РФ (MOEX) с общими полями."""
    data = {
        "sentiment_score": 0.80,
        "sentiment_label": "bullish",
        "confidence": 0.95,
        "impact_magnitude": 8,
        "time_horizon": "immediate_1h_4h",
        "information_type": "hard_fact",
        "market_surprise": "better_than_expected",
        "transmission_channel": "dividend_catalyst",
        "affected_assets": [
            {"ticker": "SBER", "sentiment": 0.85, "reason": "Рекордные дивиденды выше ожиданий консенсуса"},
            {"ticker": "IMOEX", "sentiment": 0.50, "reason": "Вес Сбера тянет весь индекс Мосбиржи вверх"},
        ],
        "key_takeaways": [
            "Совет директоров Сбера рекомендовал дивиденды 33.3 рубля",
            "Дивидендная доходность превышает 10.5%",
        ],
        "target_horizon_hours": 4,
        "is_mean_reverting": False,
        "is_speculative": False,
        "speculation_reason": "Официальное решение Совета директоров на сервере раскрытия",
        "detected_currencies": ["SBER", "IMOEX"],
        "detected_categories": ["Dividends", "Banking"],
        "reasoning": "Высокие дивиденды обеспечивают значительный приток ликвидности частных инвесторов на Мосбирже.",
    }

    result = SentimentAnalysisResult.model_validate(data)
    assert result.sentiment_score == 0.80
    assert result.sentiment_label == SentimentLabel.BULLISH
    assert result.affected_assets[0].ticker == "SBER"
    assert result.transmission_channel.value == "dividend_catalyst"
    assert result.detected_currencies == ["SBER", "IMOEX"]
