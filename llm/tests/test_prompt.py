"""Тесты формирования промптов для LLM."""

from prompt import build_analysis_user_prompt


def test_build_analysis_user_prompt_formatting():
    """Проверка подстановки полей в пользовательский промпт."""
    prompt = build_analysis_user_prompt(
        title="SEC Approves Bitcoin ETF",
        source="CoinDesk",
        categories=["Regulation", "Bitcoin"],
        content="The Securities and Exchange Commission has approved the first spot Bitcoin ETF.",
    )

    assert "ИСТОЧНИК: CoinDesk" in prompt
    assert "КАТЕГОРИИ РЕДАКЦИИ: Regulation, Bitcoin" in prompt
    assert "ЗАГОЛОВОК: SEC Approves Bitcoin ETF" in prompt
    assert "The Securities and Exchange Commission has approved" in prompt


def test_build_analysis_user_prompt_empty_categories():
    """Проверка подстановки дефолта при отсутствии категорий."""
    prompt = build_analysis_user_prompt(
        title="Breaking News",
        source="Twitter",
        categories=[],
        content="Short text.",
    )

    assert "КАТЕГОРИИ РЕДАКЦИИ: Не указаны" in prompt


def test_build_analysis_user_prompt_content_truncation():
    """Проверка обрезки текста статьи по лимиту max_chars."""
    long_content = "A" * 1000
    prompt = build_analysis_user_prompt(
        title="Title",
        source="Source",
        categories=[],
        content=long_content,
        max_chars=200,
    )

    # Проверяем, что в результирующем промпте нет 1000 символов 'A'
    assert "A" * 200 in prompt
    assert "A" * 201 not in prompt
