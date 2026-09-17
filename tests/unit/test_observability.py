import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from lnbits.extensions.allowance import crud, views_api


class ObservabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_is_wallet_scoped_and_detects_stale_worker(self):
        wallet = SimpleNamespace(id="owned")
        for last, expected in [(int(time.time()), True), (1, False)]:
            with patch.object(
                crud,
                "get_scheduler_health",
                AsyncMock(return_value={"last_completed": last, "state": "healthy"}),
            ), patch.object(
                views_api, "get_allowances", AsyncMock(return_value=[])
            ) as read:
                result = await views_api.api_allowance_health(wallet)
                self.assertIs(result["healthy"], expected)
                read.assert_awaited_once_with("owned")

    async def test_other_wallet_cannot_access_history(self):
        app = FastAPI()
        app.include_router(views_api.allowance_api_router)
        app.dependency_overrides[views_api.require_invoice_key] = (
            lambda: SimpleNamespace(id="other")
        )
        with patch.object(
            views_api,
            "get_allowance",
            AsyncMock(return_value=SimpleNamespace(wallet="owned")),
        ), patch.object(crud, "get_payment_history", AsyncMock()) as read:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get("/api/v1/allowance/test/history")
            self.assertEqual(response.status_code, 403)
            read.assert_not_awaited()
