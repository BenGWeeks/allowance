import hashlib
import unittest
from contextlib import ExitStack
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from lnbits.exceptions import PaymentError
from lnbits.extensions.allowance import tasks, views_api
from lnbits.extensions.allowance.models import Allowance


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def allowance(self):
        return Allowance(
            id="test",
            wallet="wallet",
            name="Test",
            amount=1,
            lightning_address="test@example.invalid",
            frequency_type="weekly",
            start_datetime=datetime(2020, 1, 1, tzinfo=timezone.utc),
            next_payment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )

    async def test_host_rejections_retry_only_when_no_outgoing_payment_exists(self):
        for exception in (
            ValueError("limit"),
            PaymentError("disabled"),
            TimeoutError(),
        ):
            for stored in (
                None,
                SimpleNamespace(
                    amount=-1000,
                    extra={"allowance_id": "test"},
                    pending=True,
                    success=False,
                ),
            ):
                allowance = self.allowance()
                with ExitStack() as stack:
                    for name, value in {
                        "get_allowance": allowance,
                        "claim_payment": True,
                        "resolve_lightning_address": (
                            "https://example.invalid",
                            {"metadata": "[]"},
                        ),
                        "get_invoice_from_lnurl": "invoice",
                        "update_allowance_error": None,
                    }.items():
                        stack.enter_context(
                            patch.object(tasks, name, AsyncMock(return_value=value))
                        )
                    stack.enter_context(
                        patch.object(
                            tasks,
                            "decode_invoice",
                            return_value=SimpleNamespace(
                                payment_hash="hash",
                                amount_msat=1000,
                                description_hash=hashlib.sha256(b"[]").hexdigest(),
                                has_expired=lambda: False,
                            ),
                        )
                    )
                    lookup = stack.enter_context(
                        patch.object(
                            tasks,
                            "get_standalone_payment",
                            AsyncMock(side_effect=[None, stored, stored]),
                        )
                    )
                    stack.enter_context(
                        patch.object(
                            tasks, "pay_invoice", AsyncMock(side_effect=exception)
                        )
                    )
                    defer = stack.enter_context(
                        patch.object(
                            tasks, "defer_payment", AsyncMock(return_value=True)
                        )
                    )
                    self.assertIsNone(
                        await tasks.execute_lightning_address_payment(allowance)
                    )
                    self.assertEqual(defer.await_count, int(stored is None))
                    self.assertEqual(lookup.await_args_list[1].args, ("hash",))
                    self.assertEqual(lookup.await_args_list[1].kwargs, {})

    async def test_paused_claim_can_be_checked_without_sending(self):
        allowance = self.allowance()
        allowance.active = False
        allowance.pending_payment_hash = "hash"
        for status, expected in [
            (None, None),
            (
                SimpleNamespace(
                    amount=-1000,
                    extra={"allowance_id": allowance.id},
                    pending=True,
                    success=False,
                ),
                None,
            ),
            (
                SimpleNamespace(
                    amount=-1000,
                    extra={"allowance_id": allowance.id},
                    pending=False,
                    success=True,
                ),
                True,
            ),
        ]:
            with patch.object(
                tasks, "get_standalone_payment", AsyncMock(return_value=status)
            ), patch.object(
                tasks, "check_payment_status", AsyncMock(return_value=status)
            ), patch.object(
                tasks, "pay_invoice", AsyncMock()
            ) as pay, patch.object(
                tasks, "update_allowance_success", AsyncMock()
            ):
                self.assertIs(
                    await tasks.reconcile_payment(allowance, refresh=True), expected
                )
                pay.assert_not_awaited()

    async def test_recovery_requires_owning_wallet(self):
        app = FastAPI()
        app.include_router(views_api.allowance_api_router)
        app.dependency_overrides[views_api.require_admin_key] = lambda: SimpleNamespace(
            id="other"
        )
        with patch.object(
            views_api, "get_allowance", AsyncMock(return_value=self.allowance())
        ), patch.object(tasks, "reconcile_payment", AsyncMock()) as reconcile:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                result = await client.post("/api/v1/allowance/test/reconcile")
            self.assertEqual(result.status_code, 403)
            reconcile.assert_not_awaited()

    async def test_invoice_amount_must_match_before_claim_or_payment(self):
        for amount in [None, 999, 1001]:
            allowance = self.allowance()
            with ExitStack() as stack:
                for name, value in {
                    "get_allowance": allowance,
                    "resolve_lightning_address": (
                        "https://example.invalid",
                        {"metadata": "[]"},
                    ),
                    "get_invoice_from_lnurl": "invoice",
                    "update_allowance_error": None,
                    "defer_payment": True,
                }.items():
                    stack.enter_context(
                        patch.object(tasks, name, AsyncMock(return_value=value))
                    )
                stack.enter_context(
                    patch.object(
                        tasks,
                        "decode_invoice",
                        return_value=SimpleNamespace(
                            description_hash=hashlib.sha256(b"[]").hexdigest(),
                            has_expired=lambda: False,
                            payment_hash="hash",
                            amount_msat=amount,
                        ),
                    )
                )
                claim = stack.enter_context(
                    patch.object(tasks, "claim_payment", AsyncMock())
                )
                pay = stack.enter_context(
                    patch.object(tasks, "pay_invoice", AsyncMock())
                )
                self.assertIs(
                    await tasks.execute_lightning_address_payment(allowance), None
                )
                claim.assert_not_awaited()
                pay.assert_not_awaited()

    async def test_stale_reconciliation_does_not_report_a_terminal_result(self):
        allowance = self.allowance()
        allowance.pending_payment_hash = "old-hash"
        for success in (True, False):
            with patch.object(
                tasks,
                "get_standalone_payment",
                AsyncMock(
                    return_value=SimpleNamespace(
                        amount=-1000,
                        extra={"allowance_id": allowance.id},
                        pending=False,
                        success=success,
                    )
                ),
            ), patch.object(
                tasks, "update_allowance_success", AsyncMock(return_value=False)
            ), patch.object(
                tasks, "update_allowance_error", AsyncMock(return_value=False)
            ):
                self.assertIsNone(await tasks.reconcile_payment(allowance))

    async def test_status_lookup_failures_preserve_pending_claim(self):
        for failing_call in ("get_standalone_payment", "check_payment_status"):
            allowance = self.allowance()
            allowance.pending_payment_hash = "pending-hash"
            before = allowance.dict()
            pending = SimpleNamespace(
                amount=-1000,
                extra={"allowance_id": allowance.id},
                pending=True,
                success=False,
            )
            with patch.object(
                tasks, "get_standalone_payment", AsyncMock(return_value=pending)
            ), patch.object(
                tasks, "check_payment_status", AsyncMock(return_value=pending)
            ), patch.object(
                tasks, failing_call, AsyncMock(side_effect=TimeoutError())
            ), patch.object(
                tasks, "update_allowance_success", AsyncMock()
            ) as success, patch.object(
                tasks, "update_allowance_error", AsyncMock()
            ) as error, patch.object(
                tasks, "pay_invoice", AsyncMock()
            ) as pay:
                self.assertIsNone(
                    await tasks.reconcile_payment(allowance, refresh=True)
                )
                self.assertEqual(allowance.dict(), before)
                success.assert_not_awaited()
                error.assert_not_awaited()
                pay.assert_not_awaited()
