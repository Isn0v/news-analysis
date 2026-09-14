SELECT
    COUNT(*) AS total_evaluations,
    COUNT(DISTINCT news_id) AS total_news_evaluated,
    ROUND(AVG(volume_surge_ratio), 2) AS avg_volume_surge,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_1h = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS win_rate_1h_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_4h = TRUE)::numeric * 100.0 / 
        NULLIF(COUNT(*) FILTER (WHERE sentiment_label IN ('bullish', 'bearish')), 0), 
        1
    ) AS win_rate_4h_pct,
    ROUND(AVG(return_1h_pct) FILTER (WHERE sentiment_label = 'bullish'), 2) AS avg_bullish_return_1h,
    ROUND(AVG(return_1h_pct) FILTER (WHERE sentiment_label = 'bearish'), 2) AS avg_bearish_return_1h
FROM news_market_impact;
