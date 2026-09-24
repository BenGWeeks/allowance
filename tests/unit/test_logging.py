import io
import unittest
from unittest.mock import AsyncMock, patch

from lnbits.extensions.allowance import views_api
from loguru import logger
from starlette.exceptions import HTTPException


class LoggingTests(unittest.IsolatedAsyncioTestCase):
    async def test_exception_details_do_not_escape_to_log_or_response(self):
        output = io.StringIO()
        sink = logger.add(output)
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
