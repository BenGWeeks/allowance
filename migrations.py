# the migration file is where you build your database tables
# If you create a new release for your extension ,
# remember the migration file is like a blockchain, never edit only add!

from typing import Any

async def m001_initial(db: Any) -> None:
    """
    Initial templates table with lightning address and currency support.
    """
    await db.execute(
        """
        CREATE TABLE allowance.maintable (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            wallet TEXT NOT NULL,
            lightning_address TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'sats',
            start_date TIMESTAMP NOT NULL, -- includes day, month, hour, etc.
            frequency_type TEXT NOT NULL, -- daily, weekly, monthly, yearly, per_second
            next_payment_date TIMESTAMP NOT NULL,
            memo TEXT,
            active BOOLEAN DEFAULT TRUE,
            end_date TIMESTAMP,
            lnurlpay TEXT, -- LNURL pay string for compatibility
            total INTEGER DEFAULT 0 -- Total amount processed
        );
    """
    )
