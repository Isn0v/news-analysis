#!/usr/bin/env python3
"""
Export script: dumps all project data from PostgreSQL into CSV and JSON files.

Exports:
  1. raw_news_export.csv / .json     — all articles with LLM analysis results (flattened)
  2. market_impact_export.csv / .json — all market event-study metrics
  3. combined_export.csv / .json      — full join: article + LLM fields + market metrics

Usage:
    uv run python export.py [--output-dir ./exports] [--only raw|market|combined]

Requires: DB running and .env with POSTGRES_PASSWORD set.
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

# Load settings from market-evaluator config (reads ../.env)
from config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_default(obj: Any) -> Any:
    """JSON serializer for types not serializable by default."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  [SKIP] No data for {path.name}")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        for row in rows:
            # Serialize nested objects (JSONB) to strings in CSV
            flat = {
                k: (json.dumps(v, default=_json_default) if isinstance(v, (dict, list)) else v)
                for k, v in row.items()
            }
            writer.writerow(flat)
    print(f"  [OK] {path.name}  ({len(rows):,} rows, {path.stat().st_size / 1024:.1f} KB)")


def _write_json(path: Path, rows: list[dict]) -> None:
    if not rows:
        print(f"  [SKIP] No data for {path.name}")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2, default=_json_default)
    print(f"  [OK] {path.name}  ({len(rows):,} rows, {path.stat().st_size / 1024:.1f} KB)")


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

QUERY_RAW_NEWS = """
SELECT
    n.id,
    n.url,
    n.source,
    n.origin_source,
    n.title,
    n.authors,
    n.categories,
    n.timestamp_utc,
    n.processed,
    n.processed_at,
    n.market_evaluated,
    n.market_evaluated_at,
    -- Flattened top-level LLM fields
    (n.llm_result->>'sentiment_score')::numeric         AS sentiment_score,
    n.llm_result->>'sentiment_label'                    AS sentiment_label,
    (n.llm_result->>'confidence')::numeric              AS confidence,
    (n.llm_result->>'impact_magnitude')::int            AS impact_magnitude,
    n.llm_result->>'transmission_channel'               AS transmission_channel,
    n.llm_result->>'information_type'                   AS information_type,
    n.llm_result->>'time_horizon'                       AS time_horizon,
    n.llm_result->>'market_surprise'                    AS market_surprise,
    (n.llm_result->>'target_horizon_hours')::int        AS target_horizon_hours,
    (n.llm_result->>'is_mean_reverting')::boolean       AS is_mean_reverting,
    (n.llm_result->>'is_speculative')::boolean          AS is_speculative,
    n.llm_result->>'speculation_reason'                 AS speculation_reason,
    n.llm_result->>'reasoning'                          AS reasoning,
    n.llm_result->'detected_currencies'                 AS detected_currencies,
    n.llm_result->'detected_categories'                 AS detected_categories,
    n.llm_result->'affected_assets'                     AS affected_assets,
    n.llm_result->'key_takeaways'                       AS key_takeaways,
    -- Raw LLM error flag (for failed articles)
    CASE WHEN n.llm_result ? 'error' THEN TRUE ELSE FALSE END AS llm_error,
    n.llm_result->>'error'                              AS llm_error_message
FROM raw_news n
ORDER BY n.timestamp_utc ASC;
"""

QUERY_MARKET_IMPACT = """
SELECT
    m.id             AS impact_id,
    m.news_id,
    n.source,
    n.title,
    n.timestamp_utc  AS news_published_at,
    m.ticker,
    m.symbol,
    m.t0_timestamp,
    m.p0_price,
    m.pre_drift_pct,
    m.volume_surge_ratio,
    m.return_15m_pct,
    m.return_1h_pct,
    m.return_2h_pct,
    m.return_4h_pct,
    m.return_8h_pct,
    m.return_24h_pct,
    m.max_runup_pct,
    m.max_drawdown_pct,
    m.volatility_range_pct,
    m.sentiment_label,
    m.sentiment_score,
    m.impact_magnitude,
    m.target_horizon_hours,
    m.is_mean_reverting_expected,
    m.is_speculative,
    m.is_impulse_confirmed,
    m.is_target_horizon_aligned,
    m.is_aligned_15m,
    m.is_aligned_1h,
    m.is_aligned_4h,
    m.is_aligned_24h,
    m.evaluated_at
FROM news_market_impact m
JOIN raw_news n ON n.id = m.news_id
ORDER BY m.t0_timestamp ASC;
"""

QUERY_COMBINED = """
SELECT
    n.id             AS news_id,
    n.url,
    n.source,
    n.title,
    n.timestamp_utc  AS news_published_at,
    -- LLM
    (n.llm_result->>'sentiment_score')::numeric         AS sentiment_score,
    n.llm_result->>'sentiment_label'                    AS sentiment_label,
    (n.llm_result->>'confidence')::numeric              AS confidence,
    (n.llm_result->>'impact_magnitude')::int            AS impact_magnitude,
    n.llm_result->>'transmission_channel'               AS transmission_channel,
    n.llm_result->>'information_type'                   AS information_type,
    (n.llm_result->>'target_horizon_hours')::int        AS target_horizon_hours,
    (n.llm_result->>'is_mean_reverting')::boolean       AS is_mean_reverting,
    (n.llm_result->>'is_speculative')::boolean          AS is_speculative,
    n.llm_result->>'speculation_reason'                 AS speculation_reason,
    n.llm_result->>'reasoning'                          AS reasoning,
    -- Market
    m.ticker,
    m.symbol,
    m.t0_timestamp,
    m.p0_price,
    m.pre_drift_pct,
    m.volume_surge_ratio,
    m.return_15m_pct,
    m.return_1h_pct,
    m.return_4h_pct,
    m.return_24h_pct,
    m.max_runup_pct,
    m.max_drawdown_pct,
    m.volatility_range_pct,
    m.is_impulse_confirmed,
    m.is_target_horizon_aligned,
    m.is_aligned_1h,
    m.is_aligned_4h,
    m.is_aligned_24h,
    m.evaluated_at
FROM raw_news n
JOIN news_market_impact m ON m.news_id = n.id
ORDER BY n.timestamp_utc ASC, m.ticker ASC;
"""


# ---------------------------------------------------------------------------
# Export logic
# ---------------------------------------------------------------------------

def fetch(conn: psycopg.Connection, query: str) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()


def export_all(output_dir: Path, only: str | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"\n📦 Export started — output: {output_dir.resolve()}")
    print(f"   Timestamp: {ts}")
    print(f"   Database:  {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}\n")

    with psycopg.connect(settings.postgres_dsn) as conn:

        # 1. raw_news + LLM
        if only in (None, "raw"):
            print("→ Exporting raw_news + LLM results...")
            rows = fetch(conn, QUERY_RAW_NEWS)
            _write_csv(output_dir / f"raw_news_{ts}.csv", rows)
            _write_json(output_dir / f"raw_news_{ts}.json", rows)

        # 2. market impact
        if only in (None, "market"):
            print("→ Exporting news_market_impact...")
            rows = fetch(conn, QUERY_MARKET_IMPACT)
            _write_csv(output_dir / f"market_impact_{ts}.csv", rows)
            _write_json(output_dir / f"market_impact_{ts}.json", rows)

        # 3. combined join
        if only in (None, "combined"):
            print("→ Exporting combined join (articles + LLM + market)...")
            rows = fetch(conn, QUERY_COMBINED)
            _write_csv(output_dir / f"combined_{ts}.csv", rows)
            _write_json(output_dir / f"combined_{ts}.json", rows)

    print(f"\n✅ Export complete → {output_dir.resolve()}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export crypto news analysis data to CSV and JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python export.py
  uv run python export.py --output-dir ./my_exports
  uv run python export.py --only combined
  uv run python export.py --only market --output-dir /tmp/dump
        """,
    )
    parser.add_argument(
        "--output-dir",
        default="./exports",
        help="Directory to save export files (default: ./exports)",
    )
    parser.add_argument(
        "--only",
        choices=["raw", "market", "combined"],
        default=None,
        help="Export only one dataset instead of all three",
    )
    args = parser.parse_args()

    try:
        export_all(Path(args.output_dir), only=args.only)
    except Exception as e:
        print(f"\n❌ Export failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
