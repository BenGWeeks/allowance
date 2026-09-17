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

    async def test_definitive_rejection_is_terminal_but_unknown_is_guarded(self):
        for exception, expected in [
            (PaymentError("balance", status="failed"), False),
            (PaymentError("unknown"), None),
            (TimeoutError(), None),
        ]:
            allowance = self.allowance()
            with ExitStack() as stack:
                for name, value in {
                    "get_allowance": allowance,
                    "claim_payment": True,
                    "resolve_lightning_address": ("https://example.invalid", {}),
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
                            payment_hash="hash", amount_msat=1000
                        ),
                    )
                )
                stack.enter_context(
                    patch.object(tasks, "pay_invoice", AsyncMock(side_effect=exception))
                )
                self.assertIs(
                    await tasks.execute_lightning_address_payment(allowance), expected
                )
                self.assertEqual(allowance.pending_payment_hash, "hash")

    async def test_paused_claim_can_be_checked_without_sending(self):
        allowance = self.allowance()
        allowance.active = False
        allowance.pending_payment_hash = "hash"
        for status, expected in [
            (None, None),
            (SimpleNamespace(pending=True, success=False), None),
            (SimpleNamespace(pending=False, success=True), True),
        ]:
            with patch.object(
                tasks, "get_standalone_payment", AsyncMock(return_value=status)
            ), patch.object(
                tasks, "check_transaction_status", AsyncMock(return_value=status)
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
                    "resolve_lightning_address": ("https://example.invalid", {}),
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
                            payment_hash="hash", amount_msat=amount
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
                    await tasks.execute_lightning_address_payment(allowance), False
                )
                claim.assert_not_awaited()
                pay.assert_not_awaited()
