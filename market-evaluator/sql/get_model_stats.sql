SELECT
    COALESCE(llm_model, 'unknown') AS model,
    COUNT(*) AS total_evals,
    COUNT(*) FILTER (WHERE is_speculative = FALSE) AS factual_evals,
    ROUND(AVG(volume_surge_ratio), 2) AS avg_vol_surge,
    ROUND(
        COUNT(*) FILTER (WHERE is_impulse_confirmed = TRUE AND is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15))::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS factual_impulse_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_aligned_4h = TRUE AND is_speculative = FALSE)::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = FALSE AND is_aligned_4h IS NOT NULL AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS factual_dir_4h_pct,
    ROUND(
        COUNT(*) FILTER (WHERE is_speculative = TRUE AND metrics_detail->>'trajectory' = 'FADED')::numeric * 100.0 /
        NULLIF(COUNT(*) FILTER (WHERE is_speculative = TRUE AND is_impulse_confirmed = TRUE AND (sentiment_label IN ('bullish', 'bearish') OR ABS(sentiment_score) >= 0.15)), 0),
        1
    ) AS fade_rate_pct
FROM news_market_impact
GROUP BY COALESCE(llm_model, 'unknown')
ORDER BY total_evals DESC;
