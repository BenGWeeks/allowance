# Data models for your extension

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, validator


class CreateAllowanceData(BaseModel):
    id: Optional[str] = ""
    name: str
    wallet: Optional[str]
    lightning_address: str  # Lightning address like user@domain.com or LNURL
    amount: float = 0
    currency: str = "sats"
    start_datetime: datetime
    frequency_type: str
    next_payment_date: datetime
    memo: str
    active: bool = True
    end_datetime: Optional[datetime] = None
    lnurlpay: Optional[str] = None  # LNURL pay string for compatibility
    total: float = 0  # Total amount processed
    created_at: Optional[datetime] = None  # Auto-set by database

    @validator("start_datetime", "next_payment_date", "end_datetime", "created_at")
    def timestamps_are_utc(cls, value):  # noqa: N805
        # PostgreSQL TIMESTAMP columns return naive datetimes representing UTC.
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @validator("amount")
    def amount_must_be_positive(cls, v):  # noqa: N805
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class Allowance(BaseModel):
    id: str
    name: str
    wallet: Optional[str] = None
    lightning_address: str
    amount: float = 0
    currency: str = "sats"
    start_datetime: datetime
    frequency_type: str
    next_payment_date: datetime
    memo: Optional[str] = ""
    active: bool = True
    end_datetime: Optional[datetime] = None
    lnurlpay: Optional[str] = None  # LNURL pay string for compatibility
    total: Optional[float] = 0  # Total amount processed
    created_at: Optional[datetime] = None  # When the allowance was created
    last_error: Optional[str] = None  # Last error message
    last_error_time: Optional[datetime] = None  # When the last error occurred
    last_success_time: Optional[datetime] = (
        None  # When the last successful payment was made
    )

    @validator(
        "start_datetime",
        "next_payment_date",
        "end_datetime",
        "created_at",
        "last_error_time",
        "last_success_time",
    )
    def timestamps_are_utc(cls, value):  # noqa: N805
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @validator("amount")
    def amount_must_be_positive(cls, v):  # noqa: N805
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
