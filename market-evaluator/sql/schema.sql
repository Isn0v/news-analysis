CREATE TABLE IF NOT EXISTS news_market_impact (
    id BIGSERIAL PRIMARY KEY,
    news_id BIGINT NOT NULL REFERENCES raw_news(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    t0_timestamp TIMESTAMPTZ NOT NULL,
    p0_price NUMERIC NOT NULL,
    pre_drift_pct NUMERIC,
    volume_surge_ratio NUMERIC,
    return_15m_pct NUMERIC,
    return_1h_pct NUMERIC,
    return_2h_pct NUMERIC,
    return_4h_pct NUMERIC,
    return_8h_pct NUMERIC,
    return_24h_pct NUMERIC,
    max_runup_pct NUMERIC,
    max_drawdown_pct NUMERIC,
    volatility_range_pct NUMERIC,
    sentiment_label VARCHAR(20),
    sentiment_score NUMERIC,
    impact_magnitude INT,
    target_horizon_hours INT,
    is_mean_reverting_expected BOOLEAN,
    is_impulse_confirmed BOOLEAN,
    is_target_horizon_aligned BOOLEAN,
    is_speculative BOOLEAN DEFAULT FALSE,
    is_aligned_15m BOOLEAN,
    is_aligned_1h BOOLEAN,
    is_aligned_4h BOOLEAN,
    is_aligned_24h BOOLEAN,
    metrics_detail JSONB,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_news_ticker UNIQUE (news_id, ticker)
);

CREATE INDEX IF NOT EXISTS idx_market_impact_news_id ON news_market_impact(news_id);
CREATE INDEX IF NOT EXISTS idx_market_impact_ticker ON news_market_impact(ticker);
CREATE INDEX IF NOT EXISTS idx_market_impact_t0 ON news_market_impact(t0_timestamp DESC);
