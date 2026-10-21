SELECT
    COUNT(*) AS total_evaluations,
    COUNT(DISTINCT news_id) AS total_news_evaluated,
    ROUND(AVG(volume_surge_ratio), 2) AS avg_volume_surge,
    
    -- Структура выборки (Факты vs Спекуляции)
    COUNT(*) FILTER (WHERE is_speculative = FALSE) AS factual_evals,
    COUNT(*) FILTER (WHERE is_speculative = TRUE) AS speculative_evals,
    COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)) AS factual_dir_evals,
    COUNT(*) FILTER (WHERE is_speculative = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)) AS speculative_dir_evals,
    COUNT(*) FILTER (WHERE is_speculative = TRUE AND sentiment_label = 'neutral' AND ABS(sentiment_score) < 0.15) AS speculative_neutral_evals,

    -- Подтверждение первичного импульса (первые 2 часа) на направленных сигналах
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0), 
        1
    ) AS factual_impulse_rate_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0), 
        1
    ) AS speculative_impulse_rate_pct,

    -- Направленная точность (Directional Accuracy 1ч и 4ч)
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE AND is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND is_aligned_1h IS NOT NULL AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0), 
        1
    ) AS factual_dir_1h_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_4h = TRUE AND is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND is_aligned_4h IS NOT NULL AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0), 
        1
    ) AS factual_dir_4h_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE AND is_speculative = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND is_aligned_1h IS NOT NULL AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0), 
        1
    ) AS speculative_dir_1h_pct,

    -- Траектории: Удержание тренда (Continuation) vs Затухание (Fade) на фактах
    ROUND(
        COUNT(*) FILTER (WHERE is_speculative = FALSE AND metrics_detail->>'trajectory' = 'CONTINUATION')::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS factual_continuation_rate_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_speculative = FALSE AND metrics_detail->>'trajectory' = 'FADED')::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS factual_fade_rate_pct,

    -- Динамика спекуляций: доля затухания среди импульсов
    ROUND(
        COUNT(*) FILTER (WHERE is_speculative = TRUE AND metrics_detail->>'trajectory' = 'FADED')::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND is_impulse_confirmed = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS speculative_fade_of_impulse_pct,

    -- Всплеск объема и волатильность
    ROUND(AVG(volume_surge_ratio) FILTER (WHERE is_speculative = FALSE), 2) AS factual_avg_vol_surge,
    ROUND(AVG(volume_surge_ratio) FILTER (WHERE is_speculative = TRUE), 2) AS speculative_avg_vol_surge,
    ROUND(AVG(volatility_range_pct) FILTER (WHERE is_speculative = FALSE), 2) AS factual_avg_volatility_pct,
    ROUND(AVG(volatility_range_pct) FILTER (WHERE is_speculative = TRUE), 2) AS speculative_avg_volatility_pct
FROM news_market_impact;
