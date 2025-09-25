# the migration file is where you build your database tables
# If you create a new release for your extension ,
# remember the migration file is like a blockchain, never edit only add!

from typing import Any


async def m001_initial(db: Any) -> None:
    """
    Initial templates table with lightning address and currency support.
    Supports decimal amounts for fiat currencies.
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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    )
