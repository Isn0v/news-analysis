SELECT
    COUNT(*) AS total_evaluations,
    COUNT(DISTINCT news_id) AS total_news_evaluated,
    ROUND(AVG(volume_surge_ratio), 2) AS avg_volume_surge,
    
    -- Разделение выборки
    COUNT(*) FILTER (WHERE is_speculative = FALSE) AS factual_evals,
    COUNT(*) FILTER (WHERE is_speculative = TRUE) AS speculative_evals,

    -- Win Rate импульса: Все / Факты / Спекуляции
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*), 0), 
        1
    ) AS total_impulse_win_rate_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = FALSE)::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE), 0), 
        1
    ) AS factual_impulse_win_rate_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE), 0), 
        1
    ) AS speculative_impulse_win_rate_pct,

    -- Направленная точность 1ч: Факты vs Спекуляции
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE AND is_speculative = FALSE AND sentiment_label IN ('bullish', 'bearish'))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS factual_directional_1h_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE AND is_speculative = TRUE AND sentiment_label IN ('bullish', 'bearish'))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS speculative_directional_1h_pct,

    -- Средняя волатильность размаха: Факты vs Спекуляции
    ROUND(AVG(volatility_range_pct) FILTER (WHERE is_speculative = FALSE), 2) AS factual_avg_volatility_pct,
    ROUND(AVG(volatility_range_pct) FILTER (WHERE is_speculative = TRUE), 2) AS speculative_avg_volatility_pct,

    -- Всплеск объема: Факты vs Спекуляции
    ROUND(AVG(volume_surge_ratio) FILTER (WHERE is_speculative = FALSE), 2) AS factual_avg_vol_surge,
    ROUND(AVG(volume_surge_ratio) FILTER (WHERE is_speculative = TRUE), 2) AS speculative_avg_vol_surge
FROM news_market_impact;
