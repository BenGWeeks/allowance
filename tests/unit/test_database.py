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
        await migrations.m006_operational_history(self.database)
        await migrations.m007_retry_and_local_schedule(self.database)

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

    async def test_history_commits_once_with_schedule_and_is_deleted_with_parent(self):
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        allowance = await crud.create_allowance(
            CreateAllowanceData(
                name="History",
                wallet="wallet",
                lightning_address="test@example.invalid",
                amount=1,
                start_datetime=start,
                next_payment_date=start,
                frequency_type="weekly",
                memo="",
            )
        )
        self.assertTrue(await crud.claim_payment(allowance, "history-hash"))
        allowance.pending_payment_hash = "history-hash"
        next_date = datetime(2090, 1, 1, tzinfo=timezone.utc)
        await crud.finish_payment_attempt(allowance, next_date, True)
        await crud.finish_payment_attempt(allowance, next_date, True)
        history = await crud.get_payment_history(allowance.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["outcome"], "succeeded")
        self.assertEqual(history[0]["payment_hash"], "history-hash")
        self.assertEqual(history[0]["scheduled_at"], int(start.timestamp()))
        await crud.delete_allowance(allowance.id)
        self.assertEqual(await crud.get_payment_history(allowance.id), [])

    async def test_heartbeat_persists(self):
        self.assertEqual((await crud.get_scheduler_health())["state"], "starting")
        await crud.record_scheduler_heartbeat("running")
        await crud.record_scheduler_heartbeat("healthy")
        health = await crud.get_scheduler_health()
        self.assertEqual(health["state"], "healthy")
        self.assertGreater(health["last_completed"], 0)

    async def history_fixture(self):
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        allowance = await crud.create_allowance(
            CreateAllowanceData(
                name="Rollback",
                wallet="wallet",
                lightning_address="test@example.invalid",
                amount=1,
                start_datetime=start,
                next_payment_date=start,
                frequency_type="weekly",
                memo="",
            )
        )
        self.assertTrue(await crud.claim_payment(allowance, "rollback-hash"))
        return await crud.get_allowance(allowance.id)

    async def test_history_insert_failure_rolls_back_schedule_and_claim(self):
        allowance = await self.history_fixture()
        execute = crud.TransactionConnection.execute

        async def fail_history(connection, query, values=None):
            if "INSERT INTO" in query and "payment_history" in query:
                raise RuntimeError("Injected history failure")
            return await execute(connection, query, values)

        with patch.object(crud.TransactionConnection, "execute", fail_history):
            with self.assertRaisesRegex(RuntimeError, "Injected history"):
                await crud.finish_payment_attempt(
                    allowance, datetime(2090, 1, 1, tzinfo=timezone.utc), True
                )
        loaded = await crud.get_allowance(allowance.id)
        self.assertEqual(loaded.next_payment_date, allowance.next_payment_date)
        self.assertEqual(loaded.pending_payment_hash, allowance.pending_payment_hash)
        self.assertEqual(loaded.revision, allowance.revision)
        self.assertEqual(await crud.get_payment_history(allowance.id), [])

    async def test_delete_failure_preserves_allowance_and_history(self):
        allowance = await self.history_fixture()
        await crud.finish_payment_attempt(allowance, None, True)
        execute = crud.TransactionConnection.execute

        async def fail_parent(connection, query, values=None):
            if "DELETE FROM" in query and "maintable" in query:
                raise RuntimeError("Injected parent deletion failure")
            return await execute(connection, query, values)

        with patch.object(crud.TransactionConnection, "execute", fail_parent):
            with self.assertRaisesRegex(RuntimeError, "Injected parent"):
                await crud.delete_allowance(allowance.id)
        self.assertIsNotNone(await crud.get_allowance(allowance.id))
        self.assertEqual(len(await crud.get_payment_history(allowance.id)), 1)

    async def test_history_migration_failure_rolls_back_schema_and_can_retry(self):
        for table in ("payment_history", "scheduler_health"):
            await self.database.execute(
                f"DROP TABLE {self.database.references_schema}{table}"
            )
        execute = crud.TransactionConnection.execute

        async def fail_seed(connection, query, values=None):
            if "INSERT INTO" in query and "scheduler_health" in query:
                raise RuntimeError("Injected migration seed failure")
            return await execute(connection, query, values)

        with patch.object(crud.TransactionConnection, "execute", fail_seed):
            async with self.database.connect() as connection:
                with self.assertRaisesRegex(RuntimeError, "Injected migration"):
                    await migrations.m006_operational_history(connection)
        if self.database.type == POSTGRES:
            tables = await self.database.fetchall(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = :schema AND table_name IN "
                "('payment_history', 'scheduler_health')",
                {"schema": self.database.schema},
            )
        else:
            tables = await self.database.fetchall(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name IN ('payment_history', 'scheduler_health')"
            )
        self.assertEqual(tables, [])
        async with self.database.connect() as connection:
            await migrations.m006_operational_history(connection)
        self.assertEqual((await crud.get_scheduler_health())["state"], "starting")
        self.assertEqual(await crud.get_payment_history("missing"), [])

    async def test_history_migration_retry_preserves_committed_data(self):
        allowance = await self.history_fixture()
        await crud.finish_payment_attempt(allowance, None, True)
        await crud.record_scheduler_heartbeat("healthy")
        before = await crud.get_scheduler_health()
        async with self.database.connect() as connection:
            await migrations.m006_operational_history(connection)
        self.assertEqual(await crud.get_scheduler_health(), before)
        self.assertEqual(len(await crud.get_payment_history(allowance.id)), 1)

    async def test_invalid_stored_amount_does_not_block_other_allowances(self):
        valid = await self.history_fixture()
        other = CreateAllowanceData(**valid.dict())
        other.id = None
        bad = await crud.create_allowance(other)
        await self.database.execute(
            f"UPDATE {self.database.references_schema}maintable "
            "SET amount = :amount WHERE id = :id",
            {"amount": 0.00001 if self.database.type == POSTGRES else 0, "id": bad.id},
        )
        self.assertEqual(
            [row.id for row in await crud.get_all_active_allowances()], [valid.id]
        )

    async def test_retry_keeps_due_date_and_fences_stale_attempts(self):
        allowance = await self.history_fixture()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.assertTrue(
            await crud.defer_payment(
                allowance, now + timedelta(minutes=1), now + timedelta(hours=1)
            )
        )
        self.assertFalse(await crud.defer_payment(allowance, now, now))
        current = await crud.get_allowance(allowance.id)
        self.assertIsNone(current.pending_payment_hash)
        self.assertEqual(current.next_payment_date, allowance.next_payment_date)
        self.assertEqual(current.retry_count, 1)
        self.assertFalse(await crud.claim_payment(current, "early-retry"))
        self.assertFalse(await crud.claim_payment(allowance, "stale-retry"))
        await crud.finish_payment_attempt(current, None, False)
        stopped = await crud.get_allowance(allowance.id)
        self.assertIsNone(stopped.retry_after)
        self.assertEqual(stopped.retry_count, 0)

    async def test_future_occurrence_cannot_be_claimed(self):
        allowance = await self.history_fixture()
        await crud.finish_payment_attempt(
            allowance, datetime(2090, 1, 1, tzinfo=timezone.utc)
        )
        current = await crud.get_allowance(allowance.id)
        self.assertFalse(await crud.claim_payment(current, "too-early"))

    async def test_paused_claims_are_selected_for_reconciliation(self):
        allowance = await self.history_fixture()
        await crud.deactivate_allowance(allowance.id)
        records = await crud.get_all_active_allowances()
        self.assertEqual([r.id for r in records], [allowance.id])

    async def test_wallet_quota_and_timezone_persist(self):
        allowance = await self.history_fixture()
        data = CreateAllowanceData(**allowance.dict())
        data.timezone_name = "Europe/London"
        with patch.object(crud, "MAX_ALLOWANCES_PER_WALLET", 1):
            with self.assertRaises(crud.AllowanceLimitError):
                await crud.create_allowance(data)
            data.wallet = "other-wallet"
            created = await crud.create_allowance(data)
        self.assertEqual(
            (await crud.get_allowance(created.id)).timezone_name, "Europe/London"
        )
