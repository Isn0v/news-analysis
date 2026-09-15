"""Pydantic-схемы для структурированного анализа новостного сентимента."""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class SentimentLabel(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class InformationType(str, Enum):
    HARD_FACT = "hard_fact"              # Свершившееся событие (решение ФРС, взлом, релиз ETF)
    RUMOR_LEAK = "rumor_leak"            # Слухи, утечки, сообщения анонимных источников
    OPINION_ANALYSIS = "opinion_analysis" # Авторская колонка, теханализ, мнение аналитика
    MACRO_RELEASE = "macro_release"      # Официальные макро-данные (CPI, Non-Farm, ставка)


class MarketSurprise(str, Enum):
    BETTER_THAN_EXPECTED = "better_than_expected" # Лучше ожиданий рынка
    WORSE_THAN_EXPECTED = "worse_than_expected"   # Хуже ожиданий рынка
    IN_LINE = "in_line"                           # В рамках консенсус-прогноза
    NOT_APPLICABLE = "not_applicable"             # Неприменимо (событие вне прогнозов)


class TransmissionChannel(str, Enum):
    LIQUIDITY_AND_RATES = "liquidity_and_rates"   # Канал ликвидности (ФРС, ставки, QE/QT, DXY)
    FIAT_DEBASEMENT = "fiat_debasement"           # Обесценение фиата (инфляция, печать денег, госдолг)
    GEOPOLITICAL_RISK = "geopolitical_risk"       # Геополитика (войны, санкции, бегство в кэш/золото)
    REGULATORY = "regulatory"                     # Регулирование (SEC, MiCA, запреты, суды)
    DEFI_TECH_EXPLOIT = "defi_tech_exploit"       # Эксплойты, безопасность протоколов, форки
    GENERAL_CRYPTO = "general_crypto"             # Внутренние крипто-новости (листинги, обновления)
    NONE = "none"


class TimeHorizon(str, Enum):
    IMMEDIATE_1H_4H = "immediate_1h_4h"   # Мгновенная реакция стакана
    SHORT_TERM_1D_3D = "short_term_1d_3d" # Короткий импульс на 1-3 дня
    MEDIUM_TERM_1W_1M = "medium_term_1w_1m" # Формирование среднесрочного тренда
    LONG_TERM_MONTHS = "long_term_months" # Фундаментальный сдвиг на месяцы


class AssetImpact(BaseModel):
    ticker: str = Field(
        description="Тикер затронутого актива (напр. 'BTC', 'ETH', 'SOL', 'TOTAL_CRYPTO', 'DEFI')"
    )
    sentiment: float = Field(
        ge=-1.0, le=1.0,
        description="Сентимент конкретно для этого актива от -1.0 (медвежий) до +1.0 (бычий)"
    )
    reason: str = Field(
        description="Краткое пояснение, почему новость влияет именно так на этот тикер"
    )


class SentimentAnalysisResult(BaseModel):
    sentiment_score: float = Field(
        ge=-1.0, le=1.0,
        description="Общий агрегированный сентимент новости от -1.0 (крайне медвежий) до +1.0 (крайне бычий)"
    )
    sentiment_label: SentimentLabel = Field(
        description="Категориальный сентимент: bullish, bearish или neutral"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Степень уверенности модели в данной оценке (0.0 - 1.0)"
    )
    impact_magnitude: int = Field(
        ge=1, le=10,
        description="Сила влияния новости на рынок: 1 (незначительный шум) до 10 (рыночный шок уровня краха FTX или одобрения ETF)"
    )
    time_horizon: TimeHorizon = Field(
        description="Ожидаемый временной горизонт воздействия новости на цену"
    )
    information_type: InformationType = Field(
        description="Тип информации: факт, слух, аналитическое мнение или макро-релиз"
    )
    market_surprise: MarketSurprise = Field(
        description="Фактор неожиданности новости относительно ожиданий рынка"
    )
    transmission_channel: TransmissionChannel = Field(
        description="Макро-канал передачи влияния на рынок криптовалют"
    )
    affected_assets: List[AssetImpact] = Field(
        default_factory=list,
        description="Список конкретных тикеров/секторов и персональное влияние новости на них"
    )
    key_takeaways: List[str] = Field(
        default_factory=list,
        description="2-3 ключевых факта или вывода из новости"
    )
    target_horizon_hours: int = Field(
        default=4,
        ge=1, le=720,
        description="Ожидаемый горизонт в часах, на котором влияние новости максимально (напр. 1, 2, 4, 24, 72)"
    )
    is_mean_reverting: bool = Field(
        default=False,
        description="Ожидается ли откат/поглощение первичного импульса назад (True для слухов/FUD/колонок мнений, False для фундаментальных фактов и хаков)"
    )
    is_speculative: bool = Field(
        default=False,
        description="Является ли новость спекулятивной (прогнозы аналитиков, гадания на графиках, кликбейтные заголовки, слухи, субъективные мнения). False — для твердых фактов, регуляторики, эксплойтов, макро-релизов и официальных объявлений."
    )
    speculation_reason: str = Field(
        default="",
        description="Краткое пояснение (1 предложение): почему новость признана спекулятивной (шум/мнение) или фактологической"
    )
    detected_currencies: List[str] = Field(
        default_factory=list,
        description="Список тикеров криптовалют (напр. ['BTC', 'ETH', 'SOL', 'XRP']), непосредственно затронутых новостью"
    )
    detected_categories: List[str] = Field(
        default_factory=list,
        description="Стандартизированные категории новости (напр. ['Macro', 'Regulation', 'DeFi', 'Security/Hack', 'ETF', 'Layer 1', 'Exchange', 'Adoption'])"
    )
    reasoning: str = Field(
        description="Экономическое обоснование (Chain-of-Thought): почему и по какому механизму новость влияет на рынок"
    )
