import ast
import asyncio
import inspect
import hashlib
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from lnbits.core.models import KeyType, Wallet, WalletTypeInfo
from lnbits.extensions import allowance as extension
from lnbits.extensions.allowance import migrations, tasks, views_api
from lnbits.extensions.allowance.models import Allowance
from lnbits.task_manager import task_manager


class CompatibilityTests(unittest.IsolatedAsyncioTestCase):
    def test_migrations_do_not_import_cached_extension_modules(self):
        for node in ast.walk(ast.parse(inspect.getsource(migrations))):
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertFalse((node.module or "").startswith("lnbits.extensions"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(alias.name.startswith("lnbits.extensions"))

    def test_wallet_wrapper_is_not_monkey_patched(self):
        self.assertNotIn("adminkey", WalletTypeInfo.__dict__)
        wallet = Wallet(
            id="test", name="Wallet", user="owner", adminkey="admin", inkey="invoice"
        )
        info = WalletTypeInfo(wallet=wallet, key_type=KeyType.admin)
        self.assertEqual(views_api.get_wallet_id(info), wallet.id)
        self.assertEqual(views_api.get_wallet_user(info), wallet.user)
        self.assertEqual(views_api.get_wallet_id(wallet), wallet.id)

    async def test_start_replaces_task_and_stop_is_idempotent(self):
        try:
            extension.allowance_start()
            first = task_manager.get_task(extension.SCHEDULER_TASK_NAME)
            extension.allowance_start()
            second = task_manager.get_task(extension.SCHEDULER_TASK_NAME)
            self.assertIsNot(first, second)
            self.assertEqual(
                sum(
                    t.name == extension.SCHEDULER_TASK_NAME for t in task_manager.tasks
                ),
                1,
            )
            extension.allowance_stop()
            extension.allowance_stop()
            await asyncio.sleep(0)
            self.assertIsNone(task_manager.get_task(extension.SCHEDULER_TASK_NAME))
            self.assertTrue(first.task.cancelled())
            self.assertTrue(second.task.cancelled())
        finally:
            extension.allowance_stop()

    async def test_payment_uses_host_conversion_memo_and_status(self):
        allowance = Allowance(
            id="test",
            wallet="wallet",
            name="Pocket money",
            amount=2,
            currency="GBP",
            lightning_address="recipient@example.invalid",
            frequency_type="monthly",
            start_datetime=datetime.now(timezone.utc),
            next_payment_date=datetime.now(timezone.utc),
        )
        for success, pending in [(True, False), (False, True), (False, False)]:
            allowance.pending_payment_hash = None
            with self.subTest(success=success, pending=pending):
                with patch.object(
                    tasks, "get_allowance", AsyncMock(return_value=allowance)
                ), patch.object(
                    tasks, "claim_payment", AsyncMock(return_value=True)
                ), patch.object(
                    tasks, "get_standalone_payment", AsyncMock(return_value=None)
                ), patch.object(
                    tasks,
                    "decode_invoice",
                    return_value=SimpleNamespace(
                        description_hash=hashlib.sha256(b"[]").hexdigest(),
                        has_expired=lambda: False,
                        payment_hash="hash",
                        amount_msat=2000000,
                    ),
                ), patch.object(
                    tasks, "fiat_amount_as_satoshis", AsyncMock(return_value=2000)
                ) as convert, patch.object(
                    tasks,
                    "resolve_lightning_address",
                    AsyncMock(
                        return_value=(
                            "https://example.invalid",
                            {
                                "minSendable": 1000,
                                "maxSendable": 3000000,
                                "metadata": "[]",
                            },
                        )
                    ),
                ), patch.object(
                    tasks,
                    "get_invoice_from_lnurl",
                    AsyncMock(return_value="mock-invoice"),
                ), patch.object(
                    tasks,
                    "pay_invoice",
                    AsyncMock(
                        return_value=SimpleNamespace(
                            amount=-2000000,
                            extra={"allowance_id": allowance.id},
                            success=success,
                            pending=pending,
                        )
                    ),
                ) as pay, patch.object(
                    tasks, "update_allowance_success", AsyncMock()
                ) as record, patch.object(
                    tasks, "update_allowance_error", AsyncMock()
                ) as error:
                    self.assertEqual(
                        await tasks.execute_lightning_address_payment(allowance),
                        None if pending else success,
                    )
                    convert.assert_awaited_once_with(2, "GBP")
                    self.assertEqual(
                        pay.await_args.kwargs["description"], "Pocket money"
                    )
                    self.assertEqual(pay.await_args.kwargs["tag"], "allowance")
                    self.assertEqual(pay.await_args.kwargs["max_sat"], 2000)
                    self.assertEqual(record.await_count, int(success))
                    self.assertEqual(error.await_count, int(not success))

    async def test_currency_quote_unavailable(self):
        from lnbits.utils import exchange_rates
        from starlette.exceptions import HTTPException

        for quote in [(0, 0), (0, 100), (100, 0)]:
            with patch.object(
                exchange_rates,
                "get_fiat_rate_and_price_satoshis",
                AsyncMock(return_value=quote),
            ):
                with self.assertRaises(HTTPException) as error:
                    await views_api.api_currency_rate("GBP", None)
                self.assertEqual(error.exception.status_code, 503)
        with patch.object(
            exchange_rates,
            "get_fiat_rate_and_price_satoshis",
            AsyncMock(return_value=(100, 1000000)),
        ):
            self.assertEqual(
                await views_api.api_currency_rate("gbp", None),
                {"currency": "GBP", "rate": 100, "btc_price": 1000000},
            )

    async def test_invalid_currency_is_a_client_error(self):
        from starlette.exceptions import HTTPException

        with self.assertRaises(HTTPException) as error:
            await views_api.api_currency_rate("not-a-currency", None)
        self.assertEqual(error.exception.status_code, 400)

    async def test_pending_is_reconciled_without_another_invoice(self):
        allowance = Allowance(
            id="pending-test",
            wallet="wallet",
            name="Pending",
            amount=1,
            lightning_address="recipient@example.invalid",
            frequency_type="monthly",
            start_datetime=datetime.now(timezone.utc),
            next_payment_date=datetime.now(timezone.utc),
            pending_payment_hash="hash",
        )
        for result, expected in [
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
            (
                SimpleNamespace(
                    amount=-1000,
                    extra={"allowance_id": allowance.id},
                    pending=False,
                    success=False,
                ),
                False,
            ),
        ]:
            with patch.object(
                tasks, "get_allowance", AsyncMock(return_value=allowance)
            ), patch.object(
                tasks, "get_standalone_payment", AsyncMock(return_value=result)
            ) as lookup, patch.object(
                tasks, "resolve_lightning_address", AsyncMock()
            ) as resolve, patch.object(
                tasks, "pay_invoice", AsyncMock()
            ) as pay, patch.object(
                tasks, "update_allowance_success", AsyncMock()
            ), patch.object(
                tasks, "update_allowance_error", AsyncMock()
            ):
                self.assertIs(
                    await tasks.execute_lightning_address_payment(allowance), expected
                )
                lookup.assert_awaited_once_with("hash")
                resolve.assert_not_awaited()
                pay.assert_not_awaited()
