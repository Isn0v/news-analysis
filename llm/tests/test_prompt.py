"""Tests for LLM prompt construction and parameterization."""

from prompt import build_analysis_user_prompt


def test_build_analysis_user_prompt_formatting():
    """Verify field substitution into user prompt template."""
    prompt = build_analysis_user_prompt(
        title="SEC Approves Bitcoin ETF",
        source="CoinDesk",
        categories=["Regulation", "Bitcoin"],
        content="The Securities and Exchange Commission has approved the first spot Bitcoin ETF.",
    )

    assert "SOURCE: CoinDesk" in prompt
    assert "EDITORIAL CATEGORIES: Regulation, Bitcoin" in prompt
    assert "TITLE: SEC Approves Bitcoin ETF" in prompt
    assert "The Securities and Exchange Commission has approved" in prompt


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
