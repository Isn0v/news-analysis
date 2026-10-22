SELECT
    id,
    sentiment_label,
    sentiment_score,
    return_15m_pct,
    return_1h_pct,
    return_2h_pct,
    return_4h_pct,
    return_8h_pct,
    return_24h_pct,
    target_horizon_hours,
    is_mean_reverting_expected,
    is_speculative,
    metrics_detail
FROM news_market_impact;
