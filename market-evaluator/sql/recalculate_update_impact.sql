UPDATE news_market_impact
SET
    is_impulse_confirmed = %s,
    is_aligned_15m = %s,
    is_aligned_1h = %s,
    is_aligned_4h = %s,
    is_aligned_24h = %s,
    is_target_horizon_aligned = %s,
    metrics_detail = %s
WHERE id = %s;
