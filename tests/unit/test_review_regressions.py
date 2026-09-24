import asyncio
import hashlib
import unittest
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from lnbits.extensions.allowance import tasks, views, views_api
from lnbits.extensions.allowance.models import Allowance


class ReviewRegressions(unittest.IsolatedAsyncioTestCase):
    def allowance(self, **values):
        return Allowance(
            **{
                "id": "test",
                "wallet": "wallet",
                "name": "Private name",
                "amount": 1,
                "lightning_address": "test@example.invalid",
                "frequency_type": "weekly",
                "start_datetime": datetime(2020, 1, 1, tzinfo=timezone.utc),
                "next_payment_date": datetime(2020, 1, 1, tzinfo=timezone.utc),
                **values,
            }
        )

    def prepare(self, stack, allowance):
        mocks = {}
        for name, value in {
            "get_allowance": allowance,
            "claim_payment": True,
            "resolve_lightning_address": (
                "https://example.invalid",
                {"metadata": "[]", "commentAllowed": 100},
            ),
            "get_invoice_from_lnurl": "invoice",
            "get_standalone_payment": None,
            "update_allowance_error": True,
            "update_allowance_success": True,
            "defer_payment": True,
            "pay_invoice": SimpleNamespace(
                amount=-1000,
                extra={"allowance_id": allowance.id},
                success=True,
                pending=False,
            ),
        }.items():
            mocks[name] = stack.enter_context(
                patch.object(tasks, name, AsyncMock(return_value=value))
            )
        invoice = SimpleNamespace(
            payment_hash="hash",
            amount_msat=1000,
            description_hash=hashlib.sha256(b"[]").hexdigest(),
            has_expired=lambda: False,
        )
        stack.enter_context(patch.object(tasks, "decode_invoice", return_value=invoice))
        return mocks, invoice

    async def test_transient_failure_then_success_keeps_original_occurrence(self):
        allowance = self.allowance()
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            mocks["resolve_lightning_address"].side_effect = [
                TimeoutError(),
                ("https://example.invalid", {"metadata": "[]"}),
            ]
            self.assertIsNone(await tasks.execute_lightning_address_payment(allowance))
            mocks["defer_payment"].assert_awaited_once()
            self.assertTrue(await tasks.execute_lightning_address_payment(allowance))
            mocks["pay_invoice"].assert_awaited_once()
            self.assertEqual(
                allowance.next_payment_date, datetime(2020, 1, 1, tzinfo=timezone.utc)
            )

    async def test_cancelled_attempt_never_releases_claim(self):
        allowance = self.allowance()
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            mocks["pay_invoice"].side_effect = asyncio.CancelledError
            with self.assertRaises(asyncio.CancelledError):
                await tasks.execute_lightning_address_payment(allowance)
            mocks["defer_payment"].assert_not_awaited()
            self.assertEqual(allowance.pending_payment_hash, "hash")

    async def test_retry_deadline_stops_unsent_attempts(self):
        allowance = self.allowance(
            retry_deadline=datetime(2020, 1, 2, tzinfo=timezone.utc)
        )
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            self.assertFalse(await tasks.execute_lightning_address_payment(allowance))
            mocks["pay_invoice"].assert_not_awaited()
            mocks["resolve_lightning_address"].assert_not_awaited()

    async def test_private_name_is_not_sent_as_lnurl_comment(self):
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, self.allowance())
            await tasks.execute_lightning_address_payment(self.allowance())
            self.assertEqual(mocks["get_invoice_from_lnurl"].await_args.args[2], "")

    async def test_reused_mismatched_or_expired_invoices_never_pay(self):
        for defect in ("reused", "metadata", "expiry"):
            with self.subTest(defect=defect), ExitStack() as stack:
                allowance = self.allowance()
                mocks, invoice = self.prepare(stack, allowance)
                if defect == "reused":
                    mocks["get_standalone_payment"].return_value = SimpleNamespace(
                        amount=-1000, success=True
                    )
                elif defect == "metadata":
                    invoice.description_hash = "wrong"
                else:
                    invoice.has_expired = lambda: True
                self.assertIsNone(
                    await tasks.execute_lightning_address_payment(allowance)
                )
                mocks["pay_invoice"].assert_not_awaited()
                mocks["claim_payment"].assert_not_awaited()

    async def test_paused_and_expired_claims_reconcile_without_new_payment(self):
        for values in (
            {"active": False},
            {"end_datetime": datetime(2021, 1, 1, tzinfo=timezone.utc)},
        ):
            allowance = self.allowance(pending_payment_hash="hash", **values)
            with patch.object(
                tasks, "reconcile_payment", AsyncMock(return_value=True)
            ) as reconcile, patch.object(
                tasks, "execute_lightning_address_payment", AsyncMock()
            ) as pay, patch.object(
                tasks, "finish_payment_attempt", AsyncMock()
            ) as finish:
                await tasks.process_allowance(allowance, datetime.now(timezone.utc))
                reconcile.assert_awaited_once()
                pay.assert_not_awaited()
                finish.assert_awaited_once()

    async def test_slow_wallet_does_not_block_other_wallets(self):
        blocker = asyncio.Event()
        fast = asyncio.Event()
        active = set()
        maximum = 0

        async def process(allowance, now):
            nonlocal maximum
            self.assertNotIn(allowance.wallet, active)
            active.add(allowance.wallet)
            maximum = max(maximum, len(active))
            try:
                if allowance.wallet == "slow":
                    await blocker.wait()
                else:
                    fast.set()
            finally:
                active.remove(allowance.wallet)

        rows = [self.allowance(id=str(i), wallet="slow") for i in range(20)]
        rows.append(self.allowance(wallet="fast"))
        with patch.object(tasks, "process_allowance", process):
            workers = tasks.AllowanceWorkers()
            await workers.poll(rows, datetime.now(timezone.utc))
            try:
                await asyncio.wait_for(fast.wait(), 0.5)
            finally:
                blocker.set()
                await asyncio.gather(*workers.running.values())
                await workers.close()
        self.assertLessEqual(maximum, 8)

    async def test_removed_template_and_trigger_routes_return_not_found(self):
        app = FastAPI()
        app.include_router(views.allowance_generic_router)
        app.include_router(views_api.allowance_api_router)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for path in (
                "/test-minimal",
                "/private-id",
                "/manifest/private-id.webmanifest",
            ):
                self.assertEqual((await client.get(path)).status_code, 404)
            self.assertEqual(
                (await client.post("/api/v1/allowance/private-id/trigger")).status_code,
                404,
            )

    async def test_failed_global_lookup_does_not_release_a_claim(self):
        allowance = self.allowance()
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            mocks["pay_invoice"].side_effect = ValueError("host rejection")
            mocks["get_standalone_payment"].side_effect = [None, TimeoutError()]
            self.assertIsNone(await tasks.execute_lightning_address_payment(allowance))
            mocks["defer_payment"].assert_not_awaited()
            self.assertEqual(allowance.pending_payment_hash, "hash")

    async def test_polling_continues_while_another_wallet_is_blocked(self):
        now = datetime.now(timezone.utc)
        slow_release = asyncio.Event()
        fast_paid = asyncio.Event()
        future = self.allowance(
            id="future", wallet="fast", next_payment_date=now + timedelta(minutes=2)
        )
        slow = [self.allowance(id=str(i), wallet="slow") for i in range(100)]

        async def process(allowance, _now):
            if allowance.wallet == "slow":
                await slow_release.wait()
            else:
                fast_paid.set()

        workers = tasks.AllowanceWorkers()
        with patch.object(tasks, "process_allowance", process):
            try:
                await workers.poll([*slow, future], now)
                self.assertFalse(fast_paid.is_set())
                await workers.poll([*slow, future], now + timedelta(minutes=2))
                await asyncio.wait_for(fast_paid.wait(), 0.5)
                self.assertFalse(workers.running["slow"].done())
            finally:
                slow_release.set()
                await workers.close()

    async def test_retry_expiry_preserves_the_following_due_occurrence(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        due = now - timedelta(days=1)
        allowance = self.allowance(
            start_datetime=due,
            next_payment_date=due,
            frequency_type="daily",
            retry_deadline=now,
        )
        with patch.object(
            tasks, "execute_lightning_address_payment", AsyncMock(return_value=False)
        ), patch.object(tasks, "finish_payment_attempt", AsyncMock()) as finish:
            await tasks.process_allowance(allowance, now)
            finish.assert_awaited_once_with(allowance, now, False)

    async def test_other_wallet_invoice_claim_is_released_by_its_own_caller(self):
        allowance = self.allowance()
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            mocks["pay_invoice"].side_effect = ValueError("already paid")
            other = SimpleNamespace(
                amount=-1000, pending=True, extra={"allowance_id": "other"}
            )
            mocks["get_standalone_payment"].side_effect = [None, other]
            self.assertIsNone(await tasks.execute_lightning_address_payment(allowance))
            mocks["defer_payment"].assert_awaited_once()

    async def test_claimed_calls_are_not_wrapped_in_cancelling_timeouts(self):
        now = datetime.now(timezone.utc)
        gate = asyncio.Event()
        started = asyncio.Event()
        rows = [self.allowance(id=str(i), wallet=str(i)) for i in range(9)]
        paid = []
        lock = asyncio.Lock()

        async def process(allowance, _now):
            async with lock:
                started.set()
                await gate.wait()
                paid.append(allowance.id)

        workers = tasks.AllowanceWorkers()
        with patch.object(tasks, "process_allowance", process), patch.object(
            tasks.asyncio,
            "wait_for",
            side_effect=AssertionError("Do not cancel claimed calls"),
        ):
            try:
                await workers.poll(rows, now)
                await started.wait()
                await workers.poll(rows, now + timedelta(seconds=35))
                self.assertEqual(len(workers.running), 8)
                self.assertTrue(
                    all(not t.cancelled() for t in workers.running.values())
                )
                gate.set()
                await asyncio.gather(*workers.running.values())
                await workers.poll([rows[-1]], now + timedelta(minutes=1))
                await asyncio.gather(*workers.running.values())
                self.assertCountEqual(paid, [str(i) for i in range(9)])
            finally:
                await workers.close()

    async def test_real_signed_invoice_metadata_and_expiry_are_compatible(self):
        from lnbits.wallets.fake import FakeWallet

        response = await FakeWallet().create_invoice(
            amount=1, description_hash=hashlib.sha256(b"[]").digest()
        )
        decode = tasks.decode_invoice
        decoded = decode(response.payment_request)
        self.assertEqual(decoded.description_hash, hashlib.sha256(b"[]").hexdigest())
        self.assertFalse(decoded.has_expired())
        allowance = self.allowance()
        with ExitStack() as stack:
            mocks, _ = self.prepare(stack, allowance)
            stack.enter_context(
                patch.object(tasks, "decode_invoice", side_effect=decode)
            )
            mocks["get_invoice_from_lnurl"].return_value = response.payment_request
            self.assertTrue(await tasks.execute_lightning_address_payment(allowance))
            mocks["pay_invoice"].assert_awaited_once()
