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
        await migrations.m003_namespace_cockroach_table(self.database)
        await migrations.m004_pending_payment(self.database)
        await migrations.m005_allowance_revision(self.database)

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
            loaded, "Temporary failure", int(start.timestamp())
        )
        loaded = await crud.get_allowance(created.id)
        self.assertEqual(loaded.last_error, "Temporary failure")
        self.assertEqual(loaded.last_error_time, start)
        await crud.update_allowance_success(loaded, int(next_date.timestamp()))
        loaded = await crud.get_allowance(created.id)
        self.assertIsNone(loaded.last_error)
        self.assertEqual(loaded.last_success_time, next_date)
        self.assertEqual(len(await crud.get_allowances(["test-wallet"])), 1)
        self.assertEqual(await crud.get_allowances(["other-wallet"]), [])
        # Only one concurrent caller can own an occurrence. A persisted guard
        # survives reload and stale completion cannot release someone else's hash.
        self.assertTrue(await crud.claim_payment(loaded, "payment-one"))
        self.assertFalse(await crud.claim_payment(loaded, "payment-two"))
        pending = await crud.get_allowance(created.id)
        self.assertEqual(pending.pending_payment_hash, "payment-one")
        await crud.finish_payment_attempt(loaded, next_date + timedelta(days=1))
        self.assertEqual(
            (await crud.get_allowance(created.id)).pending_payment_hash, "payment-one"
        )
        await crud.finish_payment_attempt(pending, next_date + timedelta(days=1))
        finished = await crud.get_allowance(created.id)
        self.assertIsNone(finished.pending_payment_hash)
        self.assertEqual(finished.next_payment_date, next_date + timedelta(days=1))
        self.assertFalse(await crud.claim_payment(pending, "stale-occurrence"))
        await crud.deactivate_allowance(created.id)
        self.assertEqual(await crud.get_all_active_allowances(), [])
        await crud.delete_allowance(created.id)
        self.assertIsNone(await crud.get_allowance(created.id))

    async def test_edits_and_claims_cannot_use_stale_state(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        created = await crud.create_allowance(
            CreateAllowanceData(
                name="Race",
                wallet="wallet",
                lightning_address="test@example.invalid",
                amount=1,
                start_datetime=now - timedelta(days=1),
                next_payment_date=now,
                frequency_type="weekly",
                memo="",
            )
        )
        stale = CreateAllowanceData(**created.dict())
        future = now + timedelta(days=7)
        await crud.finish_payment_attempt(created, future)
        stale.name = "Renamed"
        with self.assertRaises(crud.AllowanceConflictError):
            await crud.update_allowance(stale)
        current = await crud.get_allowance(created.id)
        self.assertEqual(current.next_payment_date, future)
        edited = CreateAllowanceData(**current.dict())
        edited.next_payment_date = now  # editable updates must ignore this field
        edited.name = "Renamed"
        updated = await crud.update_allowance(edited)
        self.assertEqual(updated.next_payment_date, future)
        self.assertFalse(await crud.claim_payment(current, "stale-edit"))
        await crud.deactivate_allowance(created.id)
        paused = await crud.get_allowance(created.id)
        self.assertFalse(await crud.claim_payment(paused, "paused"))
        self.assertFalse(await crud.claim_payment(updated, "stale-active"))

    async def test_stale_expiry_cannot_deactivate_an_edited_allowance(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        allowance = await crud.create_allowance(
            CreateAllowanceData(
                name="Expiry race",
                wallet="wallet",
                lightning_address="test@example.invalid",
                amount=1,
                start_datetime=now,
                next_payment_date=now,
                frequency_type="weekly",
                memo="",
            )
        )
        edit = CreateAllowanceData(**allowance.dict())
        edit.end_datetime = now + timedelta(days=7)
        current = await crud.update_allowance(edit)
        await crud.deactivate_allowance(allowance.id, revision=allowance.revision)
        self.assertTrue((await crud.get_allowance(allowance.id)).active)
        await crud.deactivate_allowance(current.id, revision=current.revision)
        self.assertFalse((await crud.get_allowance(current.id)).active)

    async def test_stale_payment_metadata_cannot_overwrite_a_new_occurrence(self):
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        original = await crud.create_allowance(
            CreateAllowanceData(
                name="Reconciliation race",
                wallet="wallet",
                amount=1,
                lightning_address="test@example.invalid",
                start_datetime=start,
                next_payment_date=start,
                frequency_type="weekly",
                memo="",
            )
        )
        self.assertTrue(await crud.claim_payment(original, "first-hash"))
        self.assertFalse(
            await crud.update_allowance_error(original, "Pre-claim error", 1)
        )
        old = await crud.get_allowance(original.id)
        await crud.finish_payment_attempt(old, start + timedelta(days=7))
        current = await crud.get_allowance(original.id)
        self.assertTrue(await crud.claim_payment(current, "second-hash"))
        current = await crud.get_allowance(original.id)
        self.assertTrue(await crud.update_allowance_success(current, 2000))
        self.assertTrue(
            await crud.update_allowance_error(current, "Current error", 2001)
        )
        self.assertFalse(await crud.update_allowance_success(old, 1000))
        self.assertFalse(await crud.update_allowance_error(old, "Stale error", 1001))
        old.pending_payment_hash = current.pending_payment_hash
        self.assertFalse(await crud.update_allowance_success(old, 1000))
        loaded = await crud.get_allowance(original.id)
        self.assertEqual(int(loaded.last_success_time.timestamp()), 2000)
        self.assertEqual(loaded.last_error, "Current error")
        self.assertEqual(int(loaded.last_error_time.timestamp()), 2001)
