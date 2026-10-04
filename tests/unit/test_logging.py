import io
import unittest
from unittest.mock import AsyncMock, patch

from lnbits.extensions.allowance import views_api
from loguru import logger
from starlette.exceptions import HTTPException


class LoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_exception_details_do_not_escape_to_log_or_response(self):
        output = io.StringIO()
        sink = logger.add(output, level="WARNING")
        try:
            with patch(
                "lnbits.utils.exchange_rates.get_fiat_rate_and_price_satoshis",
                AsyncMock(side_effect=RuntimeError("SECRET wallet key and memo")),
            ):
                with self.assertRaises(HTTPException) as error:
                    await views_api.api_currency_rate("GBP", None)
            self.assertEqual(error.exception.status_code, 503)
            self.assertNotIn("SECRET", str(error.exception.detail))
            self.assertNotIn("SECRET", output.getvalue())
        finally:
            logger.remove(sink)

    async def test_private_address_failure_explains_reason_without_secrets(self):
        from datetime import datetime, timezone

        from lnbits.extensions.allowance import tasks
        from lnbits.extensions.allowance.models import Allowance
        from lnbits.extensions.allowance.safe_http import PrivateLNURLAddressError

        allowance = Allowance(
            id="SECRET-ID",
            wallet="SECRET-WALLET",
            name="SECRET-NAME",
            amount=1,
            lightning_address="SECRET@example.invalid",
            frequency_type="weekly",
            start_datetime=datetime(2020, 1, 1, tzinfo=timezone.utc),
            next_payment_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        output = io.StringIO()
        sink = logger.add(output, level="WARNING")
        try:
            with patch.object(
                tasks, "get_allowance", AsyncMock(return_value=allowance)
            ), patch.object(
                tasks,
                "resolve_lightning_address",
                AsyncMock(side_effect=PrivateLNURLAddressError("SECRET")),
            ), patch.object(
                tasks, "update_allowance_error", AsyncMock()
            ) as record, patch.object(
                tasks, "defer_payment", AsyncMock(return_value=True)
            ), patch.object(
                tasks, "pay_invoice", AsyncMock()
            ) as pay:
                await tasks.execute_lightning_address_payment(allowance)
            self.assertEqual(
                record.await_args.kwargs,
                {"stage": "address_lookup", "code": "private_address"},
            )
            self.assertIn("private or otherwise disallowed", record.await_args.args[1])
            self.assertIn("private_address", output.getvalue())
            self.assertNotIn("SECRET", output.getvalue())
            self.assertNotIn("SECRET", record.await_args.args[1])
            pay.assert_not_awaited()
            code, message = tasks.payment_diagnostic(
                "payment_submission", RuntimeError("SECRET invoice credentials")
            )
            self.assertEqual(code, "payment_submission_failed")
            self.assertNotIn("SECRET", message)
        finally:
            logger.remove(sink)

    async def test_real_lnurl_lookup_with_split_dns_reports_private_address(self):
        import asyncio
        import socket

        from lnbits.extensions.allowance.safe_http import PrivateLNURLAddressError
        from lnbits.extensions.allowance.tasks import (
            payment_diagnostic,
            resolve_lightning_address,
        )

        with patch.object(
            asyncio.get_running_loop(),
            "getaddrinfo",
            AsyncMock(
                return_value=[
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        socket.IPPROTO_TCP,
                        "",
                        ("192.168.1.89", 443),
                    )
                ]
            ),
        ):
            with self.assertRaises(PrivateLNURLAddressError) as caught:
                await resolve_lightning_address("recipient@example.invalid")
        code, message = payment_diagnostic("address_lookup", caught.exception)
        self.assertEqual(code, "private_address")
        self.assertNotIn("recipient", message)
        self.assertNotIn("192.168.1.89", message)
