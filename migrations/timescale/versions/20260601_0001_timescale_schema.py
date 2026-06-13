"""Create Timescale market_events and decision_traces schema.

Revision ID: 20260601_0001
Revises:
Create Date: 2026-06-01 00:00:00
"""

from __future__ import annotations

from alembic import op

revision = "20260601_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            decision_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            payload JSONB NOT NULL
        )
        """
    )

    # S1 compatibility: convert legacy text payload to JSONB when applicable.
    op.execute(
        """
        DO $$
        DECLARE
            payload_type TEXT;
        BEGIN
            SELECT data_type
            INTO payload_type
            FROM information_schema.columns
            WHERE table_name = 'decisions'
              AND column_name = 'payload';

            IF payload_type = 'text' THEN
                ALTER TABLE decisions
                    ALTER COLUMN payload TYPE JSONB USING payload::jsonb;
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS market_events (
            decision_id TEXT PRIMARY KEY REFERENCES decisions(decision_id) ON DELETE CASCADE,
            ts TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            price DOUBLE PRECISION NOT NULL,
            volume DOUBLE PRECISION NOT NULL
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS decision_traces (
            decision_id TEXT PRIMARY KEY REFERENCES decisions(decision_id) ON DELETE CASCADE,
            ts TIMESTAMPTZ NOT NULL,
            model_name TEXT NOT NULL,
            rationale TEXT NOT NULL,
            faithfulness_score DOUBLE PRECISION,
            assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
            warnings JSONB NOT NULL DEFAULT '[]'::jsonb
        )
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_market_events_symbol_ts "
        "ON market_events(symbol, ts DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_decision_traces_model_ts "
        "ON decision_traces(model_name, ts DESC)"
    )

    op.execute(
        "SELECT create_hypertable("
        "'market_events', 'ts', if_not_exists => TRUE, migrate_data => TRUE"
        ")"
    )
    op.execute(
        "SELECT create_hypertable("
        "'decision_traces', 'ts', if_not_exists => TRUE, migrate_data => TRUE"
        ")"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS decision_traces")
    op.execute("DROP TABLE IF EXISTS market_events")