from datetime import datetime, timezone
from typing import Optional, Union

from lnbits.db import POSTGRES, Database
from lnbits.helpers import urlsafe_short_hash

from .models import Allowance, CreateAllowanceData


class AllowanceDatabase(Database):
    """Bind epochs as UTC wall-clock values for our legacy TIMESTAMP columns."""

    def timestamp_placeholder(self, key: str) -> str:
        placeholder = super().timestamp_placeholder(key)
        if self.type == POSTGRES:
            return f"({placeholder} AT TIME ZONE 'UTC')"
        return placeholder


db = AllowanceDatabase("ext_allowance")


async def create_allowance(data: CreateAllowanceData) -> Allowance:
    from datetime import datetime

    data.id = urlsafe_short_hash()

    # Convert datetime objects to timestamps (integers) for database
    start_ts: Union[datetime, int] = data.start_datetime
    if isinstance(start_ts, datetime):
        start_ts = int(start_ts.timestamp())

    next_ts: Union[datetime, int] = data.next_payment_date
    if isinstance(next_ts, datetime):
        next_ts = int(next_ts.timestamp())

    end_ts: Optional[Union[datetime, int]] = data.end_datetime
    if end_ts and isinstance(end_ts, datetime):
        end_ts = int(end_ts.timestamp())

    created_ts: Optional[Union[datetime, int]] = data.created_at
    if created_ts and isinstance(created_ts, datetime):
        created_ts = int(created_ts.timestamp())

    # Use direct SQL to avoid field name mapping issues
    # Build the SQL based on whether end_datetime is NULL
    if end_ts is None:
        sql = f"""
        INSERT INTO {db.references_schema}maintable
        (id, name, wallet, lightning_address, amount, currency,
         start_datetime, frequency_type, next_payment_date, memo,
         active, end_datetime, created_at)
        VALUES (:id, :name, :wallet, :lightning_address, :amount, :currency,
         {db.timestamp_placeholder("start_datetime")}, :frequency_type,
         {db.timestamp_placeholder("next_payment_date")}, :memo,
         :active, NULL, {db.timestamp_placeholder("created_at")})
        """
    else:
        sql = f"""
        INSERT INTO {db.references_schema}maintable
        (id, name, wallet, lightning_address, amount, currency,
         start_datetime, frequency_type, next_payment_date, memo,
         active, end_datetime, created_at)
        VALUES (:id, :name, :wallet, :lightning_address, :amount, :currency,
         {db.timestamp_placeholder("start_datetime")}, :frequency_type,
         {db.timestamp_placeholder("next_payment_date")}, :memo,
         :active, {db.timestamp_placeholder("end_datetime")},
         {db.timestamp_placeholder("created_at")})
        """

    await db.execute(
        sql,
        {
            "id": data.id,
            "name": data.name,
            "wallet": data.wallet,
            "lightning_address": data.lightning_address,
            "amount": data.amount,
            "currency": data.currency,
            "start_datetime": start_ts,
            "frequency_type": data.frequency_type,
            "next_payment_date": next_ts,
            "memo": data.memo,
            "active": data.active,
            "end_datetime": end_ts,
            "created_at": created_ts or int(datetime.now().timestamp()),
        },
    )
    return Allowance(**data.dict())


async def get_allowance(allowance_id: str) -> Optional[Allowance]:
    return await db.fetchone(
        f"SELECT * FROM {db.references_schema}maintable WHERE id = :id",
        {"id": allowance_id},
        Allowance,
    )


async def get_allowances(wallet_ids: Union[str, list[str]]) -> list[Allowance]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    if not wallet_ids:
        return []
    values = {f"wallet_{i}": wallet for i, wallet in enumerate(wallet_ids)}
    placeholders = ", ".join(f":{key}" for key in values)
    return await db.fetchall(
        f"SELECT * FROM {db.references_schema}maintable "
        f"WHERE wallet IN ({placeholders}) "
        "ORDER BY created_at DESC",
        values,
        model=Allowance,
    )


class AllowanceConflictError(Exception):
    """The record changed after the caller read it."""


async def update_allowance(data: CreateAllowanceData) -> Allowance:
    """Update editable fields without overwriting scheduler-owned state."""
    result = await db.execute(
        f"UPDATE {db.references_schema}maintable SET "
        "name = :name, lightning_address = :lightning_address, "
        "amount = :amount, currency = :currency, memo = :memo, active = :active, "
        f"end_datetime = {db.timestamp_placeholder('end')}, revision = revision + 1 "
        "WHERE id = :id AND revision = :revision",
        {
            "id": data.id,
            "revision": data.revision,
            "name": data.name,
            "lightning_address": data.lightning_address,
            "amount": data.amount,
            "currency": data.currency,
            "memo": data.memo,
            "active": data.active,
            "end": int(data.end_datetime.timestamp()) if data.end_datetime else None,
        },
    )
    if result.rowcount != 1:
        raise AllowanceConflictError("Allowance changed; reload before saving")
    updated = await get_allowance(data.id)
    if updated is None:
        raise AllowanceConflictError("Allowance was deleted")
    return updated


async def delete_allowance(allowance_id: str) -> None:
    await db.execute(
        f"DELETE FROM {db.references_schema}maintable WHERE id = :id",
        {"id": allowance_id},
    )


async def update_next_payment_date(allowance_id: str, next_payment_date) -> None:
    """Update only the next payment date for an allowance"""
    # Convert datetime to timestamp integer as LNbits stores timestamps in DB
    from datetime import datetime

    if isinstance(next_payment_date, datetime):
        next_payment_ts = int(next_payment_date.timestamp())
    else:
        next_payment_ts = next_payment_date

    # Bind the timestamp as data, just like the allowance ID.
    await db.execute(
        f"""
        UPDATE {db.references_schema}maintable
        SET next_payment_date = {db.timestamp_placeholder("next_payment_ts")},
            revision = revision + 1
        WHERE id = :id
        """,
        {"id": allowance_id, "next_payment_ts": next_payment_ts},
    )


async def deactivate_allowance(
    allowance_id: str, revision: Optional[int] = None
) -> None:
    """Deactivate an allowance"""
    await db.execute(
        f"""
        UPDATE {db.references_schema}maintable
        SET active = false, revision = revision + 1
        WHERE id = :id AND (CAST(:revision AS INTEGER) IS NULL OR revision = :revision)
        """,
        {"id": allowance_id, "revision": revision},
    )


async def get_all_active_allowances() -> list[Allowance]:
    """Get all active allowances for scheduled processing"""
    return await db.fetchall(
        f"SELECT * FROM {db.references_schema}maintable WHERE active = true "
        "ORDER BY next_payment_date",
        model=Allowance,
    )


async def update_allowance_error(
    allowance_id: str, error_message: str, error_time: int
) -> None:
    """Store error information for an allowance"""
    await db.execute(
        f"""
        UPDATE {db.references_schema}maintable
        SET last_error = :error_message,
            last_error_time = {db.timestamp_placeholder("error_time")}
        WHERE id = :allowance_id
        """,
        {
            "error_message": error_message,
            "error_time": error_time,
            "allowance_id": allowance_id,
        },
    )


async def update_allowance_success(allowance_id: str, success_time: int) -> None:
    """Clear error and store success time for an allowance"""
    await db.execute(
        f"""
        UPDATE {db.references_schema}maintable
        SET last_error = NULL,
            last_error_time = NULL,
            last_success_time = {db.timestamp_placeholder("success_time")}
        WHERE id = :allowance_id
        """,
        {"success_time": success_time, "allowance_id": allowance_id},
    )


async def clear_allowance_error(allowance_id: str) -> None:
    """Manually clear error information for an allowance"""
    await db.execute(
        f"""
        UPDATE {db.references_schema}maintable
        SET last_error = NULL,
            last_error_time = NULL
        WHERE id = :allowance_id
        """,
        {"allowance_id": allowance_id},
    )


async def claim_payment(allowance: Allowance, payment_hash: str) -> bool:
    """Claim this due occurrence before handing its invoice to LNbits."""
    result = await db.execute(
        f"UPDATE {db.references_schema}maintable "
        "SET pending_payment_hash = :hash "
        "WHERE id = :id AND pending_payment_hash IS NULL "
        "AND active = true AND revision = :revision "
        f"AND start_datetime <= {db.timestamp_placeholder('now')} "
        "AND (end_datetime IS NULL OR "
        f"end_datetime >= {db.timestamp_placeholder('now')}) "
        f"AND next_payment_date = {db.timestamp_placeholder('due')}",
        {
            "id": allowance.id,
            "hash": payment_hash,
            "revision": allowance.revision,
            "now": int(datetime.now(timezone.utc).timestamp()),
            "due": int(allowance.next_payment_date.timestamp()),
        },
    )
    return result.rowcount == 1


async def finish_payment_attempt(allowance: Allowance, next_date) -> None:
    """Atomically release this attempt and advance or finish its schedule."""
    values = {
        "id": allowance.id,
        "hash": allowance.pending_payment_hash,
        "revision": allowance.revision,
        "due": int(allowance.next_payment_date.timestamp()),
    }
    condition = (
        "pending_payment_hash = :hash"
        if allowance.pending_payment_hash
        else "pending_payment_hash IS NULL AND revision = :revision"
    )
    if next_date is None:
        assignment = "active = false"
    else:
        assignment = f"next_payment_date = {db.timestamp_placeholder('next')}"
        values["next"] = int(next_date.timestamp())
    await db.execute(
        f"UPDATE {db.references_schema}maintable SET {assignment}, "
        "pending_payment_hash = NULL, revision = revision + 1 WHERE id = :id "
        f"AND {condition} AND next_payment_date = {db.timestamp_placeholder('due')}",
        values,
    )
