"""Pydantic schemas for structured financial news sentiment analysis."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class InformationType(str, Enum):
    HARD_FACT = "hard_fact"              # Confirmed event (Fed rate decision, exploit, ETF approval/launch)
    RUMOR_LEAK = "rumor_leak"            # Rumors, anonymous sources, leaks
    OPINION_ANALYSIS = "opinion_analysis" # Op-ed, technical analysis, analyst commentary/forecast
    MACRO_RELEASE = "macro_release"      # Official macroeconomic data (CPI, Non-Farm Payrolls, FOMC)


class MarketSurprise(str, Enum):
    BETTER_THAN_EXPECTED = "better_than_expected" # Exceeded market expectations
    WORSE_THAN_EXPECTED = "worse_than_expected"   # Worse than market expectations
    IN_LINE = "in_line"                           # Matches consensus forecast
    NOT_APPLICABLE = "not_applicable"             # Qualitative event without numeric consensus


class TransmissionChannel(str, Enum):
    LIQUIDITY_AND_RATES = "liquidity_and_rates"   # Liquidity channel (Fed, interest rates, QE/QT, DXY)
    FIAT_DEBASEMENT = "fiat_debasement"           # Currency debasement (inflation, M2 expansion, sovereign debt)
    GEOPOLITICAL_RISK = "geopolitical_risk"       # Geopolitics (conflicts, sanctions, flight to cash/gold)
    REGULATORY = "regulatory"                     # Legal & enforcement (SEC, MiCA, court rulings, bans)
    DEFI_TECH_EXPLOIT = "defi_tech_exploit"       # Exploits, smart contract bugs, bridge hacks, forks
    GENERAL_CRYPTO = "general_crypto"             # Native crypto ecosystem (listings, tokenomics, mainnet)
    NONE = "none"


class TimeHorizon(str, Enum):
    IMMEDIATE_1H_4H = "immediate_1h_4h"   # Instant order book reaction (1-4h)
    SHORT_TERM_1D_3D = "short_term_1d_3d" # Momentum impulse (1-3 days)
    MEDIUM_TERM_1W_1M = "medium_term_1w_1m" # Medium-term trend formation (1-4 weeks)
    LONG_TERM_MONTHS = "long_term_months" # Multi-month structural/fundamental shift


class AssetImpact(BaseModel):
    ticker: str = Field(
        description="Standard ticker of the impacted crypto asset (e.g. 'BTC', 'ETH', 'SOL', 'XRP')"
    )
    sentiment: float = Field(
        ge=-1.0, le=1.0,
        description="Asset-specific sentiment score from -1.0 (extremely bearish) to +1.0 (extremely bullish)"
    )
    reason: str = Field(
        description="Concise rationale in English explaining why this specific ticker is affected"
    )


class SentimentAnalysisResult(BaseModel):
    sentiment_score: float = Field(
        ge=-1.0, le=1.0,
        description="Aggregated directional market sentiment score from -1.0 (extremely bearish) to +1.0 (extremely bullish)"
    )
    sentiment_label: SentimentLabel = Field(
        description="Categorical sentiment label: 'bullish' (score >= 0.10), 'bearish' (score <= -0.10), or 'neutral' (-0.10 < score < 0.10)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Model confidence score between 0.0 (uncertain) and 1.0 (high certainty)"
    )
    impact_magnitude: int = Field(
        ge=1, le=10,
        description="Market impact intensity scale from 1 (minor local noise) to 10 (market-wide systemic shock like FTX collapse or spot ETF approval)"
    )
    time_horizon: TimeHorizon = Field(
        description="Expected primary pricing horizon for this event"
    )
    information_type: InformationType = Field(
        description="Nature of the report: hard_fact, rumor_leak, opinion_analysis, or macro_release"
    )
    market_surprise: MarketSurprise = Field(
        description="Degree of surprise relative to prior market consensus"
    )
    transmission_channel: TransmissionChannel = Field(
        description="Primary macroeconomic or technical transmission channel into crypto markets"
    )
    affected_assets: List[AssetImpact] = Field(
        default_factory=list,
        description="List of specific cryptocurrency tickers directly affected with individual scores and English rationales"
    )
    key_takeaways: List[str] = Field(
        default_factory=list,
        description="2-3 key factual bullet points in English summarizing the core market drivers"
    )
    target_horizon_hours: int = Field(
        default=4,
        ge=1, le=720,
        description="Hours until maximum price impact is realized (e.g. 1-2h for liquidations/listings, 24h for macro/CPI, 72h+ for regulatory)"
    )
    is_mean_reverting: bool = Field(
        default=False,
        description="True if the price move is expected to quickly fade/mean-revert (typical for rumors, analyst targets, opinions); False for permanent fundamental catalysts"
    )
    is_speculative: bool = Field(
        default=False,
        description="True for speculative noise (price predictions, chart patterns, clickbait, unsubstantiated rumors, op-eds). False for hard factual catalysts (SEC actions, exploits, official macro releases, token listings, mainnet upgrades)"
    )
    speculation_reason: str = Field(
        default="",
        description="One concise sentence in English explaining why the news is classified as speculative noise or a hard catalyst"
    )
    detected_currencies: List[str] = Field(
        default_factory=list,
        description="List of uppercase crypto tickers mentioned (e.g. ['BTC', 'ETH']). For broad market news use ['BTC']"
    )
    detected_categories: List[str] = Field(
        default_factory=list,
        description="Standardized categories selected from: ['Macro', 'Regulation', 'ETF', 'DeFi', 'Security/Hack', 'Layer 1', 'Layer 2', 'Exchange', 'Mining', 'Adoption', 'Tokenomics', 'Derivatives', 'Market Analysis']"
    )
    reasoning: str = Field(
        description="Rigorous Chain-of-Thought economic rationale in English explaining the transmission mechanism to supply, demand, and liquidity"
    )
