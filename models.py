import math
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, StrictBool, conint, constr, root_validator, validator


class CreateAllowanceData(BaseModel):
    id: Optional[str] = ""
    name: str
    revision: int = 0
    wallet: Optional[str]
    lightning_address: str
    amount: float = 0
    currency: str = "sats"
    start_datetime: datetime
    frequency_type: str
    timezone_name: str = "UTC"
    next_payment_date: datetime
    memo: str
    active: bool = True
    end_datetime: Optional[datetime] = None
    lnurlpay: Optional[str] = None  # Retained for legacy records.
    total: float = 0
    created_at: Optional[datetime] = None

    @validator("start_datetime", "next_payment_date", "end_datetime", "created_at")
    def timestamps_are_utc(cls, value):  # noqa: N805

        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @validator("amount")
    def amount_must_be_positive(cls, v):  # noqa: N805
        if not math.isfinite(v) or v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class Allowance(BaseModel):
    id: str
    name: str
    revision: int = 0
    wallet: Optional[str] = None
    lightning_address: str
    amount: float = 0
    currency: str = "sats"
    start_datetime: datetime
    frequency_type: str
    timezone_name: str = "UTC"
    next_payment_date: datetime
    memo: Optional[str] = ""
    active: bool = True
    end_datetime: Optional[datetime] = None
    lnurlpay: Optional[str] = None  # Retained for legacy records.
    total: Optional[float] = 0
    created_at: Optional[datetime] = None
    pending_payment_hash: Optional[str] = None
    retry_count: int = 0
    retry_after: Optional[datetime] = None
    retry_deadline: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    @validator(
        "start_datetime",
        "next_payment_date",
        "end_datetime",
        "created_at",
        "last_error_time",
        "last_success_time",
        "retry_after",
        "retry_deadline",
    )
    def timestamps_are_utc(cls, value):  # noqa: N805
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @validator("amount")
    def amount_must_be_positive(cls, v):  # noqa: N805
        if not math.isfinite(v) or v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


Frequency = Literal[
    "once", "minutely", "hourly", "daily", "weekly", "monthly", "yearly"
]


class AllowanceUpdateRequest(BaseModel):
    """Only supplied fields are changed; null is reserved for clearing the end date."""

    id: Optional[str] = None
    wallet: Optional[str] = None
    revision: conint(strict=True, ge=0)
    name: Optional[
        constr(strict=True, strip_whitespace=True, min_length=1, max_length=200)
    ] = None
    lightning_address: Optional[
        constr(strict=True, strip_whitespace=True, min_length=1, max_length=2048)
    ] = None
    amount: Optional[float] = None
    currency: Optional[constr(strict=True, regex=r"^(sats|satoshis|[A-Za-z]{3})$")] = (
        None
    )
    memo: Optional[constr(strict=True, max_length=1000)] = None
    active: Optional[StrictBool] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    frequency_type: Optional[Frequency] = None
    timezone_name: Optional[constr(strict=True, max_length=100)] = None

    class Config:
        extra = "forbid"

    @root_validator(pre=True)
    def reject_null_fields(cls, values):
        if isinstance(values, dict):
            for key, value in values.items():
                if value is None and key != "end_datetime":
                    raise ValueError(f"{key} cannot be null")
        return values

    @validator("amount", pre=True)
    def valid_amount(cls, value):  # noqa: N805
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError("amount must be a finite positive number")
        amount = Decimal(str(value))
        if amount > Decimal("99999999.9999") or amount != amount.quantize(
            Decimal("0.0001")
        ):
            raise ValueError("amount must fit 8 integer and 4 decimal places")
        return value

    @validator("timezone_name")
    def valid_timezone(cls, value):  # noqa: N805
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
            raise ValueError("Unknown IANA timezone") from exc
        return value

    @validator("start_datetime", "end_datetime", pre=True)
    def iso_datetimes(cls, value):  # noqa: N805
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("date must be an ISO datetime")
        return value

    @validator("start_datetime", "end_datetime")
    def utc_datetimes(cls, value):  # noqa: N805
        if value is None:
            return value
        return (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )


class AllowanceCreateRequest(AllowanceUpdateRequest):
    timezone_name: constr(strict=True, max_length=100) = "UTC"
    revision: Optional[conint(strict=True, ge=0)] = None
    name: constr(strict=True, strip_whitespace=True, min_length=1, max_length=200)
    lightning_address: constr(
        strict=True, strip_whitespace=True, min_length=1, max_length=2048
    )
    amount: float
    currency: constr(strict=True, regex=r"^(sats|satoshis|[A-Za-z]{3})$") = "sats"
    memo: constr(strict=True, max_length=1000) = ""
    active: StrictBool = True
    start_datetime: datetime
    frequency_type: Frequency = "daily"
