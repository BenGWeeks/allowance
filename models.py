# Data models for your extension

from datetime import datetime
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

    @validator("amount")
    def amount_must_be_positive(cls, v):
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

    @validator("amount")
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v
