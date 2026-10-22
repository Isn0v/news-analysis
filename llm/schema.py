"""Pydantic schemas for structured financial news sentiment analysis."""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class InformationType(str, Enum):
    HARD_FACT = "hard_fact"  # Confirmed event (Fed rate decision, exploit, ETF approval/launch)
    RUMOR_LEAK = "rumor_leak"  # Rumors, anonymous sources, leaks
    OPINION_ANALYSIS = "opinion_analysis"  # Op-ed, technical analysis, analyst commentary/forecast
    MACRO_RELEASE = "macro_release"  # Official macroeconomic data (CPI, Non-Farm Payrolls, FOMC)


class MarketSurprise(str, Enum):
    BETTER_THAN_EXPECTED = "better_than_expected"  # Exceeded market expectations
    WORSE_THAN_EXPECTED = "worse_than_expected"  # Worse than market expectations
    IN_LINE = "in_line"  # Matches consensus forecast
    NOT_APPLICABLE = "not_applicable"  # Qualitative event without numeric consensus


class TransmissionChannel(str, Enum):
    # Универсальные макро-каналы
    LIQUIDITY_AND_RATES = "liquidity_and_rates"  # Монетарная политика, процентные ставки (ЦБ РФ / ФРС), ликвидность
    FIAT_DEBASEMENT = "fiat_debasement"  # Обесценение валюты, инфляция (ИПЦ/CPI), денежная масса
    GEOPOLITICAL_RISK = "geopolitical_risk"  # Геополитика, конфликты, санкции, внешнеторговые шоки
    REGULATORY = "regulatory"  # Регуляторные меры, законы, судебные решения, надзорные органы

    # Корпоративные и фундаментальные каналы (Equities / MOEX)
    DIVIDEND_CATALYST = "dividend_catalyst"  # Дивидендные рекомендации, отсечки, доходности
    FINANCIAL_EARNINGS = "financial_earnings"  # Финансовая отчетность (РСБУ / МСФО), чистая прибыль, выручка, EBITDA
    COMMODITY_AND_FX = "commodity_and_fx"  # Цены на сырье (Urals, Brent, газ, металлы) и курсы валют (CNY/RUB, USD/RUB)
    CORPORATE_ACTION = "corporate_action"  # Корпоративные действия: байбэки, редомициляция, M&A, допэмиссии (SPO)

    # Специфичные каналы рынков
    DEFI_TECH_EXPLOIT = "defi_tech_exploit"  # Эксплойты смарт-контрактов, взломы, технические сбои
    RETAIL_HYPE = "retail_hype"  # Эмоциональный разгон розничной толпы, пампы в Telegram-каналах
    GENERAL_MARKET = "general_market"  # Общерыночные события, листинги, ребалансировки индексов
    GENERAL_CRYPTO = "general_crypto"  # Нативная крипто-экосистема (для обратной совместимости)
    NONE = "none"


class TimeHorizon(str, Enum):
    IMMEDIATE_1H_4H = "immediate_1h_4h"  # Instant order book reaction (1-4h)
    SHORT_TERM_1D_3D = "short_term_1d_3d"  # Momentum impulse (1-3 days)
    MEDIUM_TERM_1W_1M = "medium_term_1w_1m"  # Medium-term trend formation (1-4 weeks)
    LONG_TERM_MONTHS = "long_term_months"  # Multi-month structural/fundamental shift


class AssetImpact(BaseModel):
    ticker: str = Field(
        description="Standard uppercase ticker of the impacted asset (e.g. 'SBER', 'GAZP', 'LKOH', 'IMOEX' for MOEX; 'BTC', 'ETH', 'SOL' for Crypto)"
    )
    sentiment: float = Field(
        ge=-1.0,
        le=1.0,
        description="Asset-specific sentiment score from -1.0 (extremely bearish) to +1.0 (extremely bullish)",
    )
    reason: str = Field(description="Concise rationale in English explaining why this specific ticker is affected")


class SentimentAnalysisResult(BaseModel):
    reasoning: str = Field(
        description="Rigorous Chain-of-Thought economic rationale in English explaining the transmission mechanism to supply, demand, and liquidity BEFORE determining the score and metrics"
    )
    sentiment_score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Aggregated directional market sentiment score from -1.0 (extremely bearish) to +1.0 (extremely bullish)",
    )
    sentiment_label: SentimentLabel = Field(
        description="Categorical sentiment label: 'bullish' (score >= 0.10), 'bearish' (score <= -0.10), or 'neutral' (-0.10 < score < 0.10)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Model confidence score between 0.0 (uncertain) and 1.0 (high certainty)"
    )
    impact_magnitude: int = Field(
        ge=1,
        le=10,
        description="Market impact intensity scale from 1 (minor local noise) to 10 (market-wide systemic shock like FTX collapse or spot ETF approval)",
    )
    time_horizon: TimeHorizon = Field(description="Expected primary pricing horizon for this event")
    information_type: InformationType = Field(
        description="Nature of the report: hard_fact, rumor_leak, opinion_analysis, or macro_release"
    )
    market_surprise: MarketSurprise = Field(description="Degree of surprise relative to prior market consensus")
    transmission_channel: TransmissionChannel = Field(
        description="Primary macroeconomic or technical transmission channel into crypto markets"
    )
    affected_assets: list[AssetImpact] = Field(
        default_factory=list,
        description="List of specific cryptocurrency tickers directly affected with individual scores and English rationales",
    )
    key_takeaways: list[str] = Field(
        default_factory=list, description="2-3 key factual bullet points in English summarizing the core market drivers"
    )
    target_horizon_hours: int = Field(
        default=4,
        ge=1,
        le=720,
        description="Hours until maximum price impact is realized (e.g. 1-2h for liquidations/listings, 24h for macro/CPI, 72h+ for regulatory)",
    )
    is_mean_reverting: bool = Field(
        default=False,
        description="True if the price move is expected to quickly fade/mean-revert (typical for rumors, analyst targets, opinions); False for permanent fundamental catalysts",
    )
    is_speculative: bool = Field(
        default=False,
        description="True for speculative noise (price predictions, chart patterns, clickbait, unsubstantiated rumors, op-eds). False for hard factual catalysts (SEC actions, exploits, official macro releases, token listings, mainnet upgrades)",
    )
    speculation_reason: str = Field(
        default="",
        description="One concise sentence in English explaining why the news is classified as speculative noise or a hard catalyst",
    )
    detected_currencies: list[str] = Field(
        default_factory=list,
        description="List of uppercase asset tickers mentioned (e.g. ['SBER', 'IMOEX'] for MOEX; ['BTC', 'ETH'] for crypto). For broad market events use ['IMOEX'] or ['BTC']",
    )
    detected_categories: list[str] = Field(
        default_factory=list,
        description="Standardized categories selected from: ['Macro', 'Regulation', 'Dividends', 'Earnings', 'Sanctions', 'Commodities', 'Corporate Action', 'Banking', 'ETF', 'DeFi', 'Security/Hack', 'Exchange', 'Retail Sentiment', 'Market Analysis']",
    )

    @model_validator(mode="after")
    def align_sentiment_sign_and_label(self) -> "SentimentAnalysisResult":
        """Enforces mathematical sign and label consistency between sentiment_score and sentiment_label."""
        if self.sentiment_label == SentimentLabel.BEARISH:
            if self.sentiment_score > 0:
                self.sentiment_score = -abs(self.sentiment_score)
            elif self.sentiment_score == 0.0:
                self.sentiment_score = -0.15
        elif self.sentiment_label == SentimentLabel.BULLISH:
            if self.sentiment_score < 0:
                self.sentiment_score = abs(self.sentiment_score)
            elif self.sentiment_score == 0.0:
                self.sentiment_score = 0.15
        elif self.sentiment_label == SentimentLabel.NEUTRAL:
            if self.sentiment_score >= 0.10:
                self.sentiment_label = SentimentLabel.BULLISH
            elif self.sentiment_score <= -0.10:
                self.sentiment_label = SentimentLabel.BEARISH
        return self
