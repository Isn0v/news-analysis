"""Тесты парсера и очистки ответов LLM (SentimentAnalyzer)."""

import json
import pytest
from analyzer import SentimentAnalyzer
from schema import SentimentAnalysisResult


def test_extract_json_with_think_tags():
    """Проверка очистки от тегов рассуждений DeepSeek <think>...</think>."""
    raw_llm_output = """<think>
Сначала оценим новость. Это положительное событие для рынка, так как ФРС снижает ставку.
Канал передачи - ликвидность. Сентимент будет бычьим.
</think>
{
    "sentiment_score": 0.8,
    "sentiment_label": "bullish",
    "confidence": 0.95,
    "impact_magnitude": 9,
    "time_horizon": "immediate_1h_4h",
    "information_type": "hard_fact",
    "market_surprise": "better_than_expected",
    "transmission_channel": "liquidity_and_rates",
    "affected_assets": [{"ticker": "BTC", "sentiment": 0.85, "reason": "Приток ликвидности"}],
    "key_takeaways": ["ФРС снизила ставку на 50 б.п."],
    "target_horizon_hours": 4,
    "is_mean_reverting": false,
    "is_speculative": false,
    "speculation_reason": "Официальный релиз ФРС",
    "detected_currencies": ["BTC"],
    "detected_categories": ["Macro"],
    "reasoning": "Снижение ставки удешевляет заимствования и увеличивает глобальную долларовую ликвидность."
}"""

    clean_json = SentimentAnalyzer._extract_json_from_text(raw_llm_output)
    parsed = json.loads(clean_json)

    assert parsed["sentiment_score"] == 0.8
    assert parsed["sentiment_label"] == "bullish"
    assert parsed["is_speculative"] is False
    assert parsed["detected_currencies"] == ["BTC"]

    # Проверка валидации Pydantic
    obj = SentimentAnalysisResult.model_validate_json(clean_json)
    assert obj.impact_magnitude == 9


def test_extract_json_from_markdown_codeblock():
    """Проверка извлечения JSON из markdown-блока ```json ... ```."""
    raw_llm_output = """Вот результаты вашего анализа:

```json
{
    "sentiment_score": -0.65,
    "sentiment_label": "bearish",
    "confidence": 0.85,
    "impact_magnitude": 7,
    "time_horizon": "immediate_1h_4h",
    "information_type": "hard_fact",
    "market_surprise": "worse_than_expected",
    "transmission_channel": "defi_tech_exploit",
    "affected_assets": [{"ticker": "ETH", "sentiment": -0.7, "reason": "Уязвимость смарт-контракта"}],
    "key_takeaways": ["Эксплойт на $20 млн"],
    "target_horizon_hours": 2,
    "is_mean_reverting": false,
    "is_speculative": false,
    "speculation_reason": "Подтвержденный ончейн-взлом",
    "detected_currencies": ["ETH"],
    "detected_categories": ["Security/Hack", "DeFi"],
    "reasoning": "Хак протокола подрывает доверие и провоцирует отток капитала."
}
```

Надеюсь, это поможет!"""

    clean_json = SentimentAnalyzer._extract_json_from_text(raw_llm_output)
    obj = SentimentAnalysisResult.model_validate_json(clean_json)
    assert obj.sentiment_score == -0.65
    assert obj.sentiment_label == "bearish"
    assert "Security/Hack" in obj.detected_categories


def test_extract_json_raw_braces():
    """Проверка извлечения JSON с окружающим сопроводительным текстом без codeblock."""
    raw_llm_output = 'Результат: {"sentiment_score": 0.1, "sentiment_label": "neutral", "confidence": 0.6, "impact_magnitude": 2, "time_horizon": "immediate_1h_4h", "information_type": "opinion_analysis", "market_surprise": "not_applicable", "transmission_channel": "none", "reasoning": "нейтрально"} - конец ответа.'
    clean_json = SentimentAnalyzer._extract_json_from_text(raw_llm_output)
    assert clean_json.startswith("{")
    assert clean_json.endswith("}")
    obj = SentimentAnalysisResult.model_validate_json(clean_json)
    assert obj.sentiment_label == "neutral"
