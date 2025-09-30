from typing import Optional, Union

from lnbits.db import Database
from lnbits.helpers import urlsafe_short_hash

from .models import Allowance, CreateAllowanceData

db = Database("ext_allowance")


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
        sql = """
        INSERT INTO maintable
        (id, name, wallet, lightning_address, amount, currency,
         start_datetime, frequency_type, next_payment_date, memo,
         active, end_datetime, created_at)
        VALUES (:id, :name, :wallet, :lightning_address, :amount, :currency,
         (:start_datetime), :frequency_type,
         (:next_payment_date), :memo,
         :active, NULL, (:created_at))
        """
    else:
        sql = """
        INSERT INTO maintable
        (id, name, wallet, lightning_address, amount, currency,
         start_datetime, frequency_type, next_payment_date, memo,
         active, end_datetime, created_at)
        VALUES (:id, :name, :wallet, :lightning_address, :amount, :currency,
         (:start_datetime), :frequency_type,
         (:next_payment_date), :memo,
         :active, (:end_datetime), (:created_at))
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

    # this is how we used to do it

    # allowance_id = urlsafe_short_hash()
    # await db.execute(
    #     """
    #     INSERT INTO maintable
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
        "SELECT * FROM maintable WHERE id = :id",
        {"id": allowance_id},
        Allowance,
    )


async def get_allowances(wallet_ids: Union[str, list[str]]) -> list[Allowance]:
    if isinstance(wallet_ids, str):
        wallet_ids = [wallet_ids]
    q = ",".join([f"'{w}'" for w in wallet_ids])
    return await db.fetchall(
        f"SELECT * FROM maintable WHERE wallet IN ({q}) ORDER BY id",
        model=Allowance,
    )


async def update_allowance(data: CreateAllowanceData) -> Allowance:
    # Use direct SQL to avoid field name mapping issues
    # Convert datetime objects to timestamps (integers) for database
    from datetime import datetime

    start_ts: Union[datetime, int] = data.start_datetime
    if isinstance(start_ts, datetime):
        start_ts = int(start_ts.timestamp())

    next_ts: Union[datetime, int] = data.next_payment_date
    if isinstance(next_ts, datetime):
        next_ts = int(next_ts.timestamp())

    end_ts: Optional[Union[datetime, int]] = data.end_datetime
    if end_ts and isinstance(end_ts, datetime):
        end_ts = int(end_ts.timestamp())

    # Build the SQL based on whether end_datetime is NULL
    if end_ts is None:
        sql = """
        UPDATE maintable
        SET name = :name, wallet = :wallet, lightning_address = :lightning_address,
            amount = :amount, currency = :currency,
            start_datetime = (:start_datetime),
            frequency_type = :frequency_type,
            next_payment_date = (:next_payment_date), memo = :memo,
            active = :active, end_datetime = NULL
        WHERE id = :id
        """
    else:
        sql = """
        UPDATE maintable
        SET name = :name, wallet = :wallet, lightning_address = :lightning_address,
            amount = :amount, currency = :currency,
            start_datetime = (:start_datetime),
            frequency_type = :frequency_type,
            next_payment_date = (:next_payment_date), memo = :memo,
            active = :active, end_datetime = (:end_datetime)
        WHERE id = :id
        """

    await db.execute(
        sql,
        {
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
            "id": data.id,
        },
    )
    return Allowance(**data.dict())
    # this is how we used to do it

    # q = ", ".join([f"{field[0]} = ?" for field in kwargs.items()])
    # await db.execute(
    #     f"UPDATE maintable SET {q} WHERE id = ?",
    #     (*kwargs.values(), allowance_id),
    # )


async def delete_allowance(allowance_id: str) -> None:
    await db.execute("DELETE FROM maintable WHERE id = :id", {"id": allowance_id})


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
        UPDATE maintable
        SET next_payment_date = ({next_payment_ts})
        WHERE id = :id
        """,
        {"id": allowance_id},
    )


async def deactivate_allowance(allowance_id: str) -> None:
    """Deactivate an allowance"""
    await db.execute(
        """
        UPDATE maintable
        SET active = false
        WHERE id = :id
        """,
        {"id": allowance_id},
    )


async def get_all_active_allowances() -> list[Allowance]:
    """Get all active allowances for scheduled processing"""
    return await db.fetchall(
        "SELECT * FROM maintable WHERE active = true " "ORDER BY next_payment_date",
        model=Allowance,
    )
