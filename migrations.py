# the migration file is where you build your database tables
# If you create a new release for your extension ,
# remember the migration file is like a blockchain, never edit only add!

from typing import Any


async def m001_initial(db: Any) -> None:
    """
    Initial templates table with lightning address and currency support.
    Supports decimal amounts for fiat currencies.
    Includes error tracking fields.
    """
    await db.execute(
        """
        CREATE TABLE maintable (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            wallet TEXT NOT NULL,
            lightning_address TEXT NOT NULL,
            amount NUMERIC(12,4) DEFAULT 0,
            currency TEXT DEFAULT 'sats',
            start_datetime TIMESTAMP NOT NULL,
            frequency_type TEXT NOT NULL,
            next_payment_date TIMESTAMP NOT NULL,
            memo TEXT,
            active BOOLEAN DEFAULT TRUE,
            end_datetime TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_error TEXT,
            last_error_time TIMESTAMP,
            last_success_time TIMESTAMP
        );
    """
    )


async def m002_namespace_postgres_table(db: Any) -> None:
    """Move a legacy unqualified table into the extension's PostgreSQL schema."""
    from lnbits.db import POSTGRES

    if db.type != POSTGRES:
        return
    existing = await db.fetchone(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = 'maintable'",
        {"schema": db.schema},
    )
    if existing:
        return
    columns = await db.fetchall(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'maintable'"
    )
    required = {
        "wallet",
        "lightning_address",
        "start_datetime",
        "frequency_type",
        "next_payment_date",
        "amount",
    }
    if not required.issubset({row["column_name"] for row in columns}):
        raise RuntimeError("Cannot identify the legacy Allowance table for migration")
    await db.execute(f"ALTER TABLE public.maintable SET SCHEMA {db.schema}")


async def m003_namespace_cockroach_table(db: Any) -> None:
    """Move historical CockroachDB tables into the extension schema."""
    from lnbits.db import COCKROACH

    if db.type != COCKROACH:
        return
    existing = await db.fetchone(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = :schema AND table_name = 'maintable'",
        {"schema": db.schema},
    )
    if not existing:
        await db.execute(f"ALTER TABLE public.maintable SET SCHEMA {db.schema}")


async def m004_pending_payment(db: Any) -> None:
    """Retain an outgoing invoice identity until its result is reconciled."""
    await db.execute(
        f"ALTER TABLE {db.references_schema}maintable "
        "ADD COLUMN pending_payment_hash TEXT"
    )


async def m005_allowance_revision(db: Any) -> None:
    """Detect edits that race with payments or other edits."""
    await db.execute(
        f"ALTER TABLE {db.references_schema}maintable "
        "ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
    )


async def m006_operational_history(db):
    from .crud import transaction

    async with transaction(db) as atomic:
        await atomic.execute(
            f"""
            CREATE TABLE {db.references_schema}payment_history (
                id TEXT PRIMARY KEY, allowance_id TEXT NOT NULL,
                scheduled_at BIGINT NOT NULL, completed_at BIGINT NOT NULL,
                outcome TEXT NOT NULL, payment_hash TEXT
            )
        """
        )
        await atomic.execute(
            f"""
            CREATE INDEX allowance_history_lookup
            ON {db.references_schema}payment_history (allowance_id, completed_at)
        """
        )
        await atomic.execute(
            f"""
            CREATE TABLE {db.references_schema}scheduler_health (
                id TEXT PRIMARY KEY, last_started BIGINT, last_completed BIGINT,
                state TEXT NOT NULL
            )
        """
        )
        await atomic.execute(
            f"INSERT INTO {db.references_schema}scheduler_health "
            "(id, state) VALUES ('worker', 'starting')"
        )
