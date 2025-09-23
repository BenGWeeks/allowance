from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import Allowance, CreateAllowanceData

db = Database("ext_allowance")


async def create_allowance(data: CreateAllowanceData) -> Allowance:
    data.id = urlsafe_short_hash()

    # Use direct SQL to avoid field name mapping issues
    await db.execute(
        """
        INSERT INTO ext_allowance.maintable
        (id, name, wallet, lightning_address, amount, currency,
         start_datetime, frequency_type, next_payment_date, memo,
         active, end_datetime, lnurlpay, total, created_at)
        VALUES (:id, :name, :wallet, :lightning_address, :amount, :currency,
         :start_datetime, :frequency_type, :next_payment_date, :memo,
         :active, :end_datetime, :lnurlpay, :total, :created_at)
        """,
        {
            "id": data.id,
            "name": data.name,
            "wallet": data.wallet,
            "lightning_address": data.lightning_address,
            "amount": data.amount,
            "currency": data.currency,
            "start_datetime": data.start_datetime,
            "frequency_type": data.frequency_type,
            "next_payment_date": data.next_payment_date,
            "memo": data.memo,
            "active": data.active,
            "end_datetime": data.end_datetime,
            "lnurlpay": data.lnurlpay,
            "total": data.total,
            "created_at": data.created_at
        },
    )
    return Allowance(**data.dict())

    # this is how we used to do it

    # allowance_id = urlsafe_short_hash()
    # await db.execute(
    #     """
    #     INSERT INTO allowance.maintable
    #     (id, wallet, name, lnurlpayamount, lnurlwithdrawamount)
    #     VALUES (?, ?, ?, ?, ?)
    #     """,
    #     (
    #         allowance_id,
    #         wallet_id,
    #         data.name,
    #         data.lnurlpayamount,
    #         data.lnurlwithdrawamount,
    #     ),
    # )
    # allowance = await get_allowance(allowance_id)
    # assert allowance, "Newly created table couldn't be retrieved"


async def get_allowance(allowance_id: str) -> Optional[Allowance]:
    return await db.fetchone(
        "SELECT * FROM ext_allowance.maintable WHERE id = :id",
        {"id": allowance_id},
        Allowance,
    )


async def get_allowances(wallet_ids: Union[str, list[str]]) -> list[Allowance]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM ext_allowance.maintable WHERE wallet IN ({q}) ORDER BY id",
        model=Allowance,
    )


async def update_allowance(data: CreateAllowanceData) -> Allowance:
    # Use direct SQL to avoid field name mapping issues
    await db.execute(
        """
        UPDATE ext_allowance.maintable
        SET name = :name, wallet = :wallet, lightning_address = :lightning_address, amount = :amount, currency = :currency,
            start_datetime = :start_datetime, frequency_type = :frequency_type, next_payment_date = :next_payment_date, memo = :memo,
            active = :active, end_datetime = :end_datetime, lnurlpay = :lnurlpay, total = :total
        WHERE id = :id
        """,
        {
            "name": data.name,
            "wallet": data.wallet,
            "lightning_address": data.lightning_address,
            "amount": data.amount,
            "currency": data.currency,
            "start_datetime": data.start_datetime,
            "frequency_type": data.frequency_type,
            "next_payment_date": data.next_payment_date,
            "memo": data.memo,
            "active": data.active,
            "end_datetime": data.end_datetime,
            "lnurlpay": data.lnurlpay,
            "total": data.total,
            "id": data.id
        },
    )
    return Allowance(**data.dict())
    # this is how we used to do it

    # q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    # await db.execute(
    #     f"UPDATE allowance.maintable SET {q} WHERE id = ?",
    #     (*kwargs.values(), allowance_id),
    # )


async def delete_allowance(allowance_id: str) -> None:
    await db.execute(
        "DELETE FROM ext_allowance.maintable WHERE id = :id", {"id": allowance_id}
    )


async def update_next_payment_date(allowance_id: str, next_payment_date) -> None:
    """Update only the next payment date for an allowance"""
    # Convert datetime to timestamp integer as LNbits stores timestamps in DB
    from datetime import datetime
    if isinstance(next_payment_date, datetime):
        next_payment_ts = int(next_payment_date.timestamp())
    else:
        next_payment_ts = next_payment_date

    # Use raw SQL without parameter substitution to bypass rewrite_values
    await db.execute(
        f"""
        UPDATE ext_allowance.maintable
        SET next_payment_date = to_timestamp({next_payment_ts})
        WHERE id = :id
        """,
        {"id": allowance_id}
    )


async def deactivate_allowance(allowance_id: str) -> None:
    """Deactivate an allowance"""
    await db.execute(
        """
        UPDATE ext_allowance.maintable
        SET active = false
        WHERE id = :id
        """,
        {"id": allowance_id}
    )


async def get_all_active_allowances() -> list[Allowance]:
    """Get all active allowances for scheduled processing"""
    return await db.fetchall(
        "SELECT * FROM ext_allowance.maintable WHERE active = true "
        "ORDER BY next_payment_date",
        model=Allowance,
    )
