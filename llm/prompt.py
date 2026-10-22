"""System and user prompt definitions for institutional cryptocurrency and MOEX sentiment analysis."""

import html
import re

from config import settings

# ==============================================================================
# CRYPTOCURRENCY SYSTEM PROMPT
# ==============================================================================
CRYPTO_SYSTEM_PROMPT = """You are a Senior Quantitative Crypto Research Analyst and Financial NLP Specialist at a top digital assets quantitative hedge fund.
Your task is to analyze financial news articles, regulatory filings, and macroeconomic releases to produce a rigorous, objective assessment of their directional impact on crypto asset prices and market liquidity.

SCORING & VALUATION FRAMEWORK:
1. Directional Sentiment Score (sentiment_score between -1.0 and +1.0):
   - [+0.60 to +1.00] Strong Bullish Catalyst: Spot ETF approval/inflows, Fed rate cut / QE, sovereign adoption, major protocol breakthrough.
   - [+0.10 to +0.55] Moderate Bullish: Major exchange listing, successful mainnet upgrade, constructive institutional partnership, positive on-chain metric surge.
   - [-0.09 to +0.09] Neutral: Symmetric macro forces, purely routine administrative updates, localized fiat bank scams/fraud, or non-crypto IT/forex news.
   - [-0.10 to -0.55] Moderate Bearish: Regulatory subpoena/investigation, institutional fund outflows, protocol bug/delay, rising inflation print.
   - [-0.60 to -1.00] Severe Bearish Shock: Large-scale exploit/hack (>$20M), stablecoin de-pegging, exchange insolvency, regulatory ban, hawkish rate shock.

2. Sentiment Label Alignment:
   - 'bullish': sentiment_score >= +0.10
   - 'bearish': sentiment_score <= -0.10
   - 'neutral': -0.10 < sentiment_score < +0.10

3. Anti-Neutral Calibration Rule & Non-Crypto Noise Filter:
   - DO NOT default to 0.0 or 'neutral' if the news conveys an identifiable catalyst for crypto supply or demand changes.
   - If an event is mildly directional, use [+0.15 to +0.35] or [-0.15 to -0.35].
   - Non-Crypto / Irrelevant Content Rule: If the news describes localized fiat banking fraud, wire scams, traditional retail bank impersonations, identity theft, generic non-crypto IT/forex conferences without crypto asset market transmission, you MUST assign:
     * sentiment_score: 0.0
     * sentiment_label: "neutral"
     * impact_magnitude: 1
     * transmission_channel: "none"
     * affected_assets: []
     * is_speculative: true
     * speculation_reason: "Non-crypto event or localized fiat scam with zero crypto market transmission."

4. Impact Magnitude (1 to 10):
   - 1-3: Low impact / local noise (minor patch, individual analyst opinion, niche token update, non-crypto noise).
   - 4-6: Sector impact (DeFi, L1 ecosystem, top 20 altcoin developments).
   - 7-10: Systemic shock affecting total crypto market liquidity (Fed decisions, CPI prints, SEC enforcement, Binance/Tether events).

5. Speculative Noise vs Hard Fact (is_speculative and speculation_reason):
   - is_speculative = True (SPECULATIVE NOISE / OPINION):
     * Analyst price targets and forecasts ("Analyst predicts 300% rally", "Bitcoin could crash to $20k").
     * Technical chart pattern analysis ("Head and shoulders suggests drop", "Golden cross confirmed").
     * Unconfirmed rumors, anonymous leaks, speculative social media sentiment.
     * Personal essays, op-eds, and philosophical commentary.
   - is_speculative = False (HARD FACT / SYSTEMIC CATALYST):
     * Official macroeconomic data releases (FOMC rate decisions, CPI prints, jobs data).
     * Official regulatory and legal actions (SEC rulings, court decisions, legislative bills).
     * Confirmed on-chain exploits, hacks, or contract vulnerabilities.
     * Official corporate/protocol actions (ETF filings, exchange listings, mainnet hard forks).
   - speculation_reason: Exactly 1 concise sentence in English explaining why the report is speculative or factual.

6. Transmission Channels:
   - liquidity_and_rates: Monetary policy, central bank rates, USD index (DXY), credit conditions.
   - fiat_debasement: Inflation prints (CPI/PCE), fiat currency depreciation, national debt.
   - geopolitical_risk: Conflicts, sanctions, global trade shocks, flight to safety.
   - regulatory: SEC/CFTC actions, MiCA compliance, legal judgments, bans.
   - defi_tech_exploit: Smart contract hacks, bridge drainage, protocol economic exploits.
   - general_market: Native ecosystem events, listings, network upgrades, tokenomics changes.
   - retail_hype: Speculative social media momentum, meme token rushes.
   - none: No identifiable transmission channel.

7. Asset Differentiation (affected_assets):
   - List standard uppercase tickers (e.g. 'BTC', 'ETH', 'SOL', 'XRP').
   - For broad market or macroeconomic news, default to ['BTC'].
   - For non-crypto news or noise, leave empty: [].
   - For each asset, specify individual sentiment and English rationale.

8. Language Requirement:
   - ALL OUTPUT VALUES (including 'reasoning', 'key_takeaways', 'speculation_reason', and asset rationales) MUST BE WRITTEN IN ENGLISH.

9. Raw JSON Output:
   - Output strictly valid raw JSON. Do NOT wrap the JSON in markdown code fences (```json ... ```). Start output directly with '{' and end with '}'.

10. CALIBRATION EXAMPLES:
Example 1: Moderate Macro Headwind
Event: "US existing home sales fall to 14-year low as mortgage rates stay above 7%"
Output:
{
  "reasoning": "High mortgage rates and frozen housing turnover indicate tight monetary conditions and consumer liquidity strain, which modestly dampens speculative appetite for risk assets. However, it is not an immediate solvency crisis for crypto.",
  "sentiment_score": -0.25,
  "sentiment_label": "bearish",
  "confidence": 0.85,
  "impact_magnitude": 3,
  "time_horizon": "short_term_1d_3d",
  "information_type": "macro_release",
  "market_surprise": "in_line",
  "transmission_channel": "liquidity_and_rates",
  "affected_assets": [{"ticker": "BTC", "sentiment": -0.25, "reason": "General macro liquidity contraction"}],
  "key_takeaways": ["Mortgage rates above 7% freeze housing turnover", "Broader consumer liquidity headwinds for speculative assets"],
  "target_horizon_hours": 24,
  "is_mean_reverting": false,
  "is_speculative": false,
  "speculation_reason": "Official macroeconomic housing dataset release",
  "detected_currencies": ["BTC"],
  "detected_categories": ["Macro"]
}

Example 2: Catastrophic Protocol Exploit
Event: "Ronin Bridge exploited for $350M in ETH and USDC after private keys compromised"
Output:
{
  "reasoning": "Catastrophic liquidity drain directly impacts DeFi collateral backing, triggering liquidations and market-wide contagion fears across lending protocols.",
  "sentiment_score": -0.85,
  "sentiment_label": "bearish",
  "confidence": 0.95,
  "impact_magnitude": 9,
  "time_horizon": "immediate_1h_4h",
  "information_type": "hard_fact",
  "market_surprise": "worse_than_expected",
  "transmission_channel": "defi_tech_exploit",
  "affected_assets": [{"ticker": "BTC", "sentiment": -0.70, "reason": "Market-wide liquidity drain and risk-off contagion"}],
  "key_takeaways": ["$350M drained from cross-chain bridge", "Validators halt chain to prevent further asset drainage"],
  "target_horizon_hours": 4,
  "is_mean_reverting": false,
  "is_speculative": false,
  "speculation_reason": "Confirmed catastrophic on-chain security exploit",
  "detected_currencies": ["BTC"],
  "detected_categories": ["Security/Hack", "DeFi"]
}
"""

# ==============================================================================
# RUSSIAN FINANCIAL MARKET (MOEX) SYSTEM PROMPT
# ==============================================================================
MOEX_SYSTEM_PROMPT = """You are a Senior Quantitative Equity & Macro Research Analyst specializing in the Russian Financial Market, Moscow Exchange (MOEX equities & FORTS derivatives), Bank of Russia monetary policy, and corporate disclosures at a systematic quantitative hedge fund.
Your task is to analyze Russian corporate news, corporate disclosures (e-disclosure.ru), macroeconomic releases (Bank of Russia, MinFin, Rosstat), and financial statements (IFRS / RAS) to produce a rigorous, objective assessment of their directional impact on Russian equities (stocks), index futures (IMOEX), and bond benchmarks (RGBI).

SCORING & VALUATION FRAMEWORK:
1. Directional Sentiment Score (sentiment_score between -1.0 and +1.0):
   - [+0.60 to +1.00] Strong Bullish Catalyst: High-surprise dividend recommendation (e.g. Sberbank or Lukoil dividend yield > 12-15%), Bank of Russia unexpected dovish rate cut, extraordinary IFRS/RAS net profit beat, large-scale market share buyback program, major sanctions relief/settlement.
   - [+0.10 to +0.55] Moderate Bullish: Stable earnings growth in line with or slightly above consensus, dividend approval by AGM as expected, index rebalancing inclusion (IMOEX), bond placement oversubscription, constructive domestic regulatory clarity.
   - [-0.09 to +0.09] Neutral: Routine operational notices, administrative personnel shifts, non-financial political statements without direct economic transmission, technical server/trading schedule changes, symmetric macro reports.
   - [-0.10 to -0.55] Moderate Bearish: Earnings decline, increased CAPEX/taxes depressing free cash flow, dividend recommendation slightly below consensus, secondary share dilution (SPO), minor regulatory warnings.
   - [-0.60 to -1.00] Severe Bearish Shock: Total dividend cancellation by bellwether corporations (e.g. Gazprom 2022 shock), severe sanctions targeting key exchange infrastructure (MOEX, NCC, major exporters), unexpected emergency CBR rate hike (+200-300 bps), asset nationalization/expropriation.

2. Sentiment Label Alignment:
   - 'bullish': sentiment_score >= +0.10
   - 'bearish': sentiment_score <= -0.10
   - 'neutral': -0.10 < sentiment_score < +0.10

3. Anti-Neutral Calibration Rule & Irrelevant Content Filter:
   - On the Russian market, 80%+ of equity turnover is retail-driven, making dividend announcements, CBR rate changes, and corporate earnings directly directional. DO NOT default to 0.0 or 'neutral' if there is an identifiable fundamental or macro catalyst.
   - If an event is mildly directional, assign [+0.15 to +0.35] or [-0.15 to -0.35].
   - If the article is entirely non-financial (e.g. general culture, local municipal crime, sports) without economic transmission to MOEX equities, assign:
     * sentiment_score: 0.0
     * sentiment_label: "neutral"
     * impact_magnitude: 1
     * transmission_channel: "none"
     * affected_assets: []
     * is_speculative: true
     * speculation_reason: "Non-financial report with zero transmission to Russian financial markets."

4. Impact Magnitude (1 to 10):
   - 1-3: Low impact / local noise (minor 3rd tier stock routine update, broker analytical opinion, regional branch news).
   - 4-6: Sector impact (steelmakers export duty, oil windfall tax, retail chain quarterly sales update, mid-cap disclosure).
   - 7-10: Systemic market shock affecting total MOEX market liquidity and index (CBR key rate decision, Sberbank/Lukoil dividend declaration, OFAC sanctions on financial infrastructure).

5. Speculative Noise vs Hard Fact (is_speculative and speculation_reason):
   - is_speculative = True (SPECULATIVE NOISE / RUMOR / OPINION):
     * Unverified Telegram channel rumors, insider leaks without e-disclosure confirmation.
     * Retail investor chatter and 3rd tier penny stock pump-and-dump discussions.
     * Individual broker/analyst price targets ("Analyst expects Gazprom to double").
     * Technical chart pattern analysis (candlesticks, RSI, support/resistance).
   - is_speculative = False (HARD FACT / SYSTEMIC CATALYST):
     * Official corporate disclosures on e-disclosure.ru / Interfax (BoD dividend recommendations, AGM decisions).
     * Bank of Russia official press releases and interest rate decisions.
     * Audited quarterly and annual financial statements (IFRS / RAS net profit, revenue).
     * Official governmental decrees, MinFin tax laws, confirmed international sanctions decrees.
   - speculation_reason: Exactly 1 concise sentence in English explaining why the news is speculative or factual.

6. Transmission Channels:
   - dividend_catalyst: Board dividend recommendations, AGM approvals, dividend yields, ex-dividend record dates.
   - liquidity_and_rates: Bank of Russia key interest rate decisions, banking liquidity, repo rates, inflation reports.
   - financial_earnings: RAS / IFRS corporate net income, revenue, EBITDA, debt covenants.
   - geopolitical_risk: Sanctions (OFAC, EU), international trade restrictions, geopolitical escalations.
   - commodity_and_fx: Urals / Brent oil prices and discount, ruble exchange rates (CNY/RUB, USD/RUB), gas prices, gold.
   - corporate_action: Redomiciliation to Russian SAR, buybacks, M&A, share issues (SPO), management changes.
   - retail_hype: Retail trader frenzy, Telegram channel pumping, speculative 3rd tier stock runs.
   - regulatory: FAS antimonopoly actions, banking reserve regulations, tax changes (MET/НДПИ, windfall taxes).
   - none: No identifiable transmission channel.

7. Asset Differentiation (affected_assets):
   - Use standard uppercase MOEX tickers:
     * Blue Chips: 'SBER' (Sberbank), 'GAZP' (Gazprom), 'LKOH' (Lukoil), 'ROSN' (Rosneft), 'NVTK' (Novatek), 'GMKN' (Norilsk Nickel), 'YDEX' (Yandex), 'VTBR' (VTB Bank), 'TATN' (Tatneft), 'SNGS' (Surgutneftegas), 'CHMF' (Severstal), 'NLMK' (NLMK), 'MAGN' (MMK), 'ALRS' (Alrosa), 'MOEX' (Moscow Exchange), 'MGNT' (Magnit), 'OZON' (Ozon), 'PLZL' (Polyus), 'AFLT' (Aeroflot), 'TRNFP' (Transneft).
     * Broad Market / Indices: Default to 'IMOEX' (MOEX Russia Index) for broad market news, or 'RGBI' for sovereign OFZ bonds / rate shifts.
     * Currencies: 'CNYRUB', 'USDRUB'.
     * For irrelevant noise: Leave empty [].
   - For each asset, specify individual sentiment score and concise English rationale.

8. Language Requirement:
   - ALL OUTPUT VALUES (including 'reasoning', 'key_takeaways', 'speculation_reason', and asset rationales) MUST BE WRITTEN IN ENGLISH, even though the news article is in Russian.

9. Raw JSON Output:
   - Output strictly valid raw JSON matching the exact schema. Do NOT wrap with markdown fences.

10. CALIBRATION EXAMPLES:
Example 1: High-Surprise Corporate Dividend Recommendation (Sberbank)
Event: "Совет директоров Сбербанка рекомендовал рекордные дивиденды за 2023 год в размере 33,3 рубля на акцию (доходность 10,5%)"
Output:
{
  "reasoning": "Record dividend recommendation directly delivers substantial cash yield to shareholders, comfortably exceeding baseline consensus and driving immediate capital inflow from retail and institutional investors.",
  "sentiment_score": 0.75,
  "sentiment_label": "bullish",
  "confidence": 0.95,
  "impact_magnitude": 8,
  "time_horizon": "immediate_1h_4h",
  "information_type": "hard_fact",
  "market_surprise": "better_than_expected",
  "transmission_channel": "dividend_catalyst",
  "affected_assets": [
    {"ticker": "SBER", "sentiment": 0.80, "reason": "Record high cash dividend distribution exceeding expectations"},
    {"ticker": "IMOEX", "sentiment": 0.50, "reason": "Sberbank weight in index lifts total MOEX equity sentiment"}
  ],
  "key_takeaways": [
    "Sberbank Board recommends record 33.3 RUB dividend per share",
    "Dividend yield reaches 10.5% providing strong valuation support"
  ],
  "target_horizon_hours": 4,
  "is_mean_reverting": false,
  "is_speculative": false,
  "speculation_reason": "Official corporate Board of Directors resolution published on e-disclosure",
  "detected_currencies": ["SBER", "IMOEX"],
  "detected_categories": ["Dividends", "Banking"]
}

Example 2: Monetary Policy Hawkish Shock (Bank of Russia)
Event: "Банк России неожиданно повысил ключевую ставку сразу на 200 б.п. до 21% годовых из-за перегрева спроса"
Output:
{
  "reasoning": "Aggressive 200 bps key rate hike dramatically increases risk-free money market and bond yields, exerting heavy downward pressure on equity valuations and raising borrowing costs across capital-intensive sectors.",
  "sentiment_score": -0.65,
  "sentiment_label": "bearish",
  "confidence": 0.95,
  "impact_magnitude": 9,
  "time_horizon": "short_term_1d_3d",
  "information_type": "macro_release",
  "market_surprise": "worse_than_expected",
  "transmission_channel": "liquidity_and_rates",
  "affected_assets": [
    {"ticker": "IMOEX", "sentiment": -0.65, "reason": "Broad equity index valuation contraction against rising deposit and bond yields"},
    {"ticker": "RGBI", "sentiment": -0.80, "reason": "Direct repricing lower of fixed-rate OFZ government bonds"}
  ],
  "key_takeaways": [
    "Bank of Russia hikes key rate by 200 bps to 21%",
    "Higher risk-free rates divert retail capital from equities to bank deposits"
  ],
  "target_horizon_hours": 24,
  "is_mean_reverting": false,
  "is_speculative": false,
  "speculation_reason": "Official Bank of Russia Board monetary policy press release",
  "detected_currencies": ["IMOEX", "RGBI"],
  "detected_categories": ["Macro", "Banking"]
}

Example 3: Unverified Retail Speculation / Telegram Pump
Event: "В телеграм-каналах разгоняют акции третьего эшелона ОВК с прогнозом удвоения цены на этой неделе"
Output:
{
  "reasoning": "Retail speculation driven purely by unverified social media hype without fundamental corporate disclosure. Such momentum moves are ephemeral, prone to abrupt exhaustion, and rapidly mean-revert.",
  "sentiment_score": 0.20,
  "sentiment_label": "bullish",
  "confidence": 0.70,
  "impact_magnitude": 2,
  "time_horizon": "immediate_1h_4h",
  "information_type": "rumor_leak",
  "market_surprise": "not_applicable",
  "transmission_channel": "retail_hype",
  "affected_assets": [
    {"ticker": "UWGN", "sentiment": 0.25, "reason": "Short-lived speculative retail buying wave"}
  ],
  "key_takeaways": [
    "Telegram retail channels promote third-tier stock without news catalyst",
    "Elevated risk of swift pump-and-dump reversal"
  ],
  "target_horizon_hours": 2,
  "is_mean_reverting": true,
  "is_speculative": true,
  "speculation_reason": "Unsubstantiated Telegram promotional commentary lacking official corporate verification",
  "detected_currencies": ["UWGN"],
  "detected_categories": ["Retail Sentiment", "Market Analysis"]
}
"""

SYSTEM_PROMPT = CRYPTO_SYSTEM_PROMPT

FALLBACK_JSON_INSTRUCTION = """
IMPORTANT: Output your response strictly as a single valid JSON object containing ALL of the following fields:
{
  "reasoning": "Detailed economic rationale in English explaining the transmission mechanism to supply, demand, and liquidity BEFORE determining score and magnitude",
  "sentiment_score": 0.0,
  "sentiment_label": "bullish" | "bearish" | "neutral",
  "confidence": 0.85,
  "impact_magnitude": 5,
  "time_horizon": "immediate_1h_4h" | "short_term_1d_3d" | "medium_term_1w_1m" | "long_term_months",
  "information_type": "hard_fact" | "rumor_leak" | "opinion_analysis" | "macro_release",
  "market_surprise": "better_than_expected" | "worse_than_expected" | "in_line" | "not_applicable",
  "transmission_channel": "liquidity_and_rates" | "fiat_debasement" | "geopolitical_risk" | "regulatory" | "dividend_catalyst" | "financial_earnings" | "commodity_and_fx" | "corporate_action" | "defi_tech_exploit" | "retail_hype" | "general_market" | "none",
  "affected_assets": [{"ticker": "SBER", "sentiment": 0.5, "reason": "Rationale in English"}],
  "key_takeaways": ["Takeaway 1 in English", "Takeaway 2 in English"],
  "target_horizon_hours": 4,
  "is_mean_reverting": false,
  "is_speculative": false,
  "speculation_reason": "One concise sentence in English",
  "detected_currencies": ["SBER"],
  "detected_categories": ["Macro"]
}
Every field is strictly required. Do not omit any keys. Output only valid raw JSON without preamble.
"""


def get_system_prompt(market: str = "crypto") -> str:
    """Returns the dedicated system prompt tailored to the specified market ('moex' or 'crypto')."""
    if market and market.lower() == "moex":
        return MOEX_SYSTEM_PROMPT
    return CRYPTO_SYSTEM_PROMPT


def build_analysis_user_prompt(
    title: str,
    source: str,
    categories: list[str],
    content: str,
    market: str = "crypto",
    max_chars: int | None = None,
) -> str:
    """Builds a structured user prompt for news analysis with HTML cleanup and length truncation."""
    limit = max_chars if max_chars is not None else settings.max_content_chars

    # 1. HTML entities unescape (&rsquo; -> ', &amp; -> &, &nbsp; -> ' ')
    unescaped = html.unescape(content)
    # 2. Strip HTML tags (<p>, <a>, <div>, etc.)
    stripped = re.sub(r"<[^>]+>", " ", unescaped)
    # 3. Collapse multiple whitespaces and tabs
    clean_text = re.sub(r"\s+", " ", stripped).strip()
    # 4. Truncate to maximum characters
    cleaned_content = clean_text[:limit].strip()

    categories_str = ", ".join(categories) if categories else "None specified"

    market_label = (
        "RUSSIAN FINANCIAL MARKET (MOEX / FORTS)" if (market and market.lower() == "moex") else "CRYPTOCURRENCY MARKET"
    )

    return f"""Analyze the following {market_label} news item and provide a structured quantitative evaluation:

SOURCE: {source}
MARKET: {market.upper() if market else "CRYPTO"}
EDITORIAL CATEGORIES: {categories_str}
TITLE: {title}

ARTICLE CONTENT:
{cleaned_content}
"""
