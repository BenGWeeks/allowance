import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from lnbits.db import POSTGRES, SQLITE
from lnbits.extensions.allowance import crud, migrations
from lnbits.extensions.allowance.models import CreateAllowanceData
from lnbits.settings import settings


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if crud.db.type == POSTGRES:
            if (
                os.environ.get("ALLOWANCE_POSTGRES_TEST") != "1"
                or os.environ.get("LNBITS_DATABASE_URL")
                != "postgres://allowance_tests@allowance-postgres-test:5432/allowance_tests"
            ):
                raise RuntimeError(
                    "PostgreSQL tests require the disposable test container"
                )
            self.database = crud.AllowanceDatabase(
                "ext_allowance_regression_" + uuid4().hex
            )
        elif crud.db.type == SQLITE:
            folder = tempfile.TemporaryDirectory(prefix="allowance-regression-")
            self.addCleanup(folder.cleanup)
            with patch.object(settings, "lnbits_data_folder", folder.name):
                self.database = crud.AllowanceDatabase("ext_allowance_regression")
        else:
            raise RuntimeError("Unsupported regression database")
        patcher = patch.object(crud, "db", self.database)
        patcher.start()
        self.addCleanup(patcher.stop)
        if self.database.type == POSTGRES:
            zone = await self.database.fetchone(
                "SELECT current_setting('TimeZone') AS zone"
            )
            self.assertEqual(zone["zone"], "America/New_York")
        await migrations.m001_initial(self.database)
        await migrations.m002_namespace_postgres_table(self.database)
        await migrations.m002_namespace_postgres_table(self.database)

    async def asyncTearDown(self):
        if self.database.type == POSTGRES:
            await self.database.execute(f"DROP SCHEMA {self.database.schema} CASCADE")
        await self.database.engine.dispose()

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
        data.id = created.id
        data.end_datetime = start + timedelta(days=365)
        await crud.update_allowance(data)
        loaded = await crud.get_allowance(created.id)
        self.assertEqual(loaded.end_datetime, data.end_datetime)
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
        self.assertEqual(loaded.last_error_time, start)
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
