"""Tests for LLM prompt construction and parameterization."""

from prompt import (
    CRYPTO_SYSTEM_PROMPT,
    MOEX_SYSTEM_PROMPT,
    build_analysis_user_prompt,
    get_system_prompt,
)


def test_get_system_prompt_routing():
    """Verify system prompt routes correctly by market."""
    moex_prompt = get_system_prompt("moex")
    assert moex_prompt == MOEX_SYSTEM_PROMPT
    assert "Moscow Exchange" in moex_prompt
    assert "SBER" in moex_prompt
    assert "dividend_catalyst" in moex_prompt

    crypto_prompt = get_system_prompt("crypto")
    assert crypto_prompt == CRYPTO_SYSTEM_PROMPT
    assert "Senior Quantitative Crypto Research Analyst" in crypto_prompt
    assert "BTC" in crypto_prompt

    default_prompt = get_system_prompt("")
    assert default_prompt == crypto_prompt


def test_build_analysis_user_prompt_formatting():
    """Verify field substitution into user prompt template."""
    prompt = build_analysis_user_prompt(
        title="SEC Approves Bitcoin ETF",
        source="CoinDesk",
        categories=["Regulation", "Bitcoin"],
        content="The Securities and Exchange Commission has approved the first spot Bitcoin ETF.",
        market="crypto",
    )

    assert "SOURCE: CoinDesk" in prompt
    assert "MARKET: CRYPTO" in prompt
    assert "EDITORIAL CATEGORIES: Regulation, Bitcoin" in prompt
    assert "TITLE: SEC Approves Bitcoin ETF" in prompt
    assert "The Securities and Exchange Commission has approved" in prompt


def test_build_analysis_user_prompt_moex_market():
    """Verify MOEX market labeling in user prompt."""
    prompt = build_analysis_user_prompt(
        title="Сбербанк рекомендовал рекордные дивиденды",
        source="rbc",
        categories=["Финансы", "Дивиденды"],
        content="Совет директоров рекомендовал выплатить 33.3 рубля на акцию.",
        market="moex",
    )

    assert "MARKET: MOEX" in prompt
    assert "RUSSIAN FINANCIAL MARKET (MOEX / FORTS)" in prompt
    assert "TITLE: Сбербанк рекомендовал рекордные дивиденды" in prompt


def test_build_analysis_user_prompt_empty_categories():
    """Verify default placeholder when categories are missing."""
    prompt = build_analysis_user_prompt(
        title="Breaking News",
        source="Twitter",
        categories=[],
        content="Short text.",
    )

    assert "EDITORIAL CATEGORIES: None specified" in prompt


def test_build_analysis_user_prompt_content_truncation():
    """Verify article text truncation by max_chars limit."""
    long_content = "A" * 1000
    prompt = build_analysis_user_prompt(
        title="Title",
        source="Source",
        categories=[],
        content=long_content,
        max_chars=200,
    )

    assert "A" * 200 in prompt
    assert "A" * 201 not in prompt


def test_build_analysis_user_prompt_html_cleaning():
    """Verify HTML tag stripping and entity unescaping in prompt builder."""
    dirty_html = (
        "<p>Bitcoin&#39;s surge &amp; Ethereum&#8217;s breakout!</p>"
        "<div class='ad'><a href='https://example.com'>Click here</a></div>"
        "   Line with   lots   of   spaces.   "
    )
    prompt = build_analysis_user_prompt(
        title="Surge News",
        source="CoinTelegraph",
        categories=["Market"],
        content=dirty_html,
    )

    assert "Bitcoin's surge & Ethereum’s breakout! Click here Line with lots of spaces." in prompt
    assert "<p>" not in prompt
    assert "<div" not in prompt
    assert "&#39;" not in prompt
    assert "&amp;" not in prompt
