import unittest
from datetime import datetime, timedelta, timezone

from lnbits.extensions.allowance import crud, migrations
from lnbits.extensions.allowance.models import CreateAllowanceData


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # The runner uses a disposable data folder in an isolated container.
        await crud.db.execute("DROP TABLE IF EXISTS maintable")
        await migrations.m001_initial(crud.db)

    async def test_persisted_schedule_and_error_tracking(self):
        start = datetime(2026, 1, 31, 9, tzinfo=timezone.utc)
        data = CreateAllowanceData(
            name="Database regression",
            wallet="test-wallet",
            lightning_address="recipient@example.invalid",
            amount=1,
            start_datetime=start,
            next_payment_date=start,
            frequency_type="monthly",
            memo="Test",
        )
        created = await crud.create_allowance(data)
        loaded = await crud.get_allowance(created.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.start_datetime, start)
        next_date = start + timedelta(days=28)
        await crud.update_next_payment_date(created.id, next_date)
        loaded = await crud.get_allowance(created.id)
        self.assertEqual(loaded.next_payment_date, next_date)
        await crud.update_allowance_error(
            created.id, "Temporary failure", int(start.timestamp())
        )
        loaded = await crud.get_allowance(created.id)
        self.assertEqual(loaded.last_error, "Temporary failure")
        await crud.update_allowance_success(created.id, int(next_date.timestamp()))
        loaded = await crud.get_allowance(created.id)
        self.assertIsNone(loaded.last_error)
        self.assertEqual(loaded.last_success_time, next_date)
        self.assertEqual(len(await crud.get_allowances(["test-wallet"])), 1)
        self.assertEqual(await crud.get_allowances(["other-wallet"]), [])
        await crud.deactivate_allowance(created.id)
        self.assertEqual(await crud.get_all_active_allowances(), [])
        await crud.delete_allowance(created.id)
        self.assertIsNone(await crud.get_allowance(created.id))
