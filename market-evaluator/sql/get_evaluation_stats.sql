SELECT
    COUNT(*) AS total_evaluations,
    COUNT(DISTINCT news_id) AS total_news_evaluated,
    ROUND(AVG(volume_surge_ratio), 2) AS avg_volume_surge,
    -- Win Rate импульса (в первые 2 часа)
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*), 0), 
        1
    ) AS impulse_win_rate_pct,
    -- Win Rate на заявленном целевом горизонте (из тех, где горизонт уже наступил)
    ROUND(
        COUNT(*) FILTER (WHERE is_target_horizon_aligned = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE is_target_horizon_aligned IS NOT NULL), 0), 
        1
    ) AS target_horizon_win_rate_pct,
    -- Направленная точность (только направленные новости bullish/bearish)
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE AND sentiment_label IN ('bullish', 'bearish'))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS directional_1h_win_rate_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_4h = TRUE AND sentiment_label IN ('bullish', 'bearish'))::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS directional_4h_win_rate_pct,
    ROUND(AVG(return_1h_pct) FILTER (WHERE sentiment_label = 'bullish'), 2) AS avg_bullish_return_1h,
    ROUND(AVG(return_1h_pct) FILTER (WHERE sentiment_label = 'bearish'), 2) AS avg_bearish_return_1h
FROM news_market_impact;
