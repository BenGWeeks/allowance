import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from lnbits.extensions.allowance import views_api
from lnbits.extensions.allowance.models import Allowance, AllowanceCreateRequest
from pydantic import ValidationError


class ValidationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.allowance = Allowance(
            id="test",
            name="Name",
            wallet="wallet",
            amount=1,
            lightning_address="test@example.invalid",
            frequency_type="weekly",
            start_datetime=datetime(2090, 1, 1, tzinfo=timezone.utc),
            next_payment_date=datetime(2090, 1, 1, tzinfo=timezone.utc),
            end_datetime=datetime(2091, 1, 1, tzinfo=timezone.utc),
        )
        app = FastAPI()
        app.include_router(views_api.allowance_api_router)
        app.dependency_overrides[views_api.require_admin_key] = lambda: SimpleNamespace(
            id="wallet", user="owner"
        )
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_invalid_updates_never_write(self):
        for data in [
            {"amount": 0},
            {"amount": 0.00001, "currency": "USD"},
            {"amount": 100000000},
            {"currency": "XYZ"},
            {"lightning_address": "not-an-address"},
            {"timezone_name": "Invalid/Zone"},
            {"amount": "NaN"},
            {"amount": True},
            {"amount": 0.5},
            {"frequency_type": "invalid"},
            {"start_datetime": "invalid"},
            {"name": "  "},
            {"end_datetime": "invalid"},
            {"active": "false"},
            {"memo": None},
            {"next_payment_date": "2090-01-01"},
            {"end_datetime": "2080-01-01T00:00:00Z"},
        ]:
            with self.subTest(data=data), patch.object(
                views_api, "get_allowance", AsyncMock(return_value=self.allowance)
            ), patch.object(views_api, "update_allowance", AsyncMock()) as save:
                response = await self.client.put(
                    "/api/v1/allowance/test", json={"revision": 0, **data}
                )
                self.assertEqual(response.status_code, 422, response.text)
                save.assert_not_awaited()

    async def test_omitted_end_preserved_and_explicit_null_clears(self):
        for payload, end in [
            ({"name": "Changed"}, self.allowance.end_datetime),
            ({"end_datetime": None}, None),
        ]:
            with patch.object(
                views_api, "get_allowance", AsyncMock(return_value=self.allowance)
            ), patch.object(
                views_api, "update_allowance", AsyncMock(return_value=self.allowance)
            ) as save:
                response = await self.client.put(
                    "/api/v1/allowance/test", json={"revision": 0, **payload}
                )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(save.await_args.args[0].end_datetime, end)

    def test_negative_offsets_and_nonfinite_amounts(self):
        values = {
            "name": "Test",
            "lightning_address": "test@example.invalid",
            "amount": 1,
            "start_datetime": "2090-01-01T18:00:00-04:00",
            "frequency_type": "weekly",
        }
        model = AllowanceCreateRequest(**values)
        self.assertEqual(
            model.start_datetime, datetime(2090, 1, 1, 22, tzinfo=timezone.utc)
        )
        for amount in [float("nan"), float("inf"), -float("inf")]:
            with self.assertRaises(ValidationError):
                AllowanceCreateRequest(**{**values, "amount": amount})

    async def test_list_failure_is_not_an_empty_success(self):
        with patch.object(
            views_api, "get_user", AsyncMock(side_effect=RuntimeError("private"))
        ):
            response = await self.client.get("/api/v1/allowance")
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("private", response.text)

    async def test_nullable_legacy_memo_and_total_can_be_edited(self):
        self.allowance.memo = None
        self.allowance.total = None
        with patch.object(
            views_api, "get_allowance", AsyncMock(return_value=self.allowance)
        ), patch.object(
            views_api, "update_allowance", AsyncMock(return_value=self.allowance)
        ) as save:
            response = await self.client.put(
                "/api/v1/allowance/test", json={"revision": 0, "name": "Renamed"}
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(save.await_args.args[0].memo, "")
            self.assertEqual(save.await_args.args[0].total, 0)

    async def test_expired_allowance_can_be_edited_without_reactivation(self):
        self.allowance.start_datetime = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.allowance.end_datetime = datetime(2021, 1, 1, tzinfo=timezone.utc)
        for active in (True, False):
            self.allowance.active = active
            for payload in ({"name": "Renamed"}, {"amount": 2}, {"active": False}):
                with self.subTest(active=active, payload=payload), patch.object(
                    views_api, "get_allowance", AsyncMock(return_value=self.allowance)
                ), patch.object(
                    views_api,
                    "update_allowance",
                    AsyncMock(return_value=self.allowance),
                ) as save:
                    response = await self.client.put(
                        "/api/v1/allowance/test", json={"revision": 0, **payload}
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    save.assert_awaited_once()

    async def test_explicit_activation_of_expired_allowance_is_rejected(self):
        self.allowance.start_datetime = datetime(2020, 1, 1, tzinfo=timezone.utc)
        self.allowance.end_datetime = datetime(2021, 1, 1, tzinfo=timezone.utc)
        for active in (True, False):
            self.allowance.active = active
            with patch.object(
                views_api, "get_allowance", AsyncMock(return_value=self.allowance)
            ), patch.object(views_api, "update_allowance", AsyncMock()) as save:
                response = await self.client.put(
                    "/api/v1/allowance/test", json={"revision": 0, "active": True}
                )
                self.assertEqual(response.status_code, 422)
                save.assert_not_awaited()

    async def test_legacy_invalid_recipient_or_currency_can_be_paused(self):
        self.allowance.currency = "XYZ"
        self.allowance.lightning_address = "legacy-invalid"
        with patch.object(
            views_api, "get_allowance", AsyncMock(return_value=self.allowance)
        ), patch.object(
            views_api, "update_allowance", AsyncMock(return_value=self.allowance)
        ) as save:
            response = await self.client.put(
                "/api/v1/allowance/test", json={"revision": 0, "active": False}
            )
            self.assertEqual(response.status_code, 200)
            save.assert_awaited_once()

    async def test_invalid_url_syntax_is_a_validation_error(self):
        with patch.object(
            views_api, "get_allowance", AsyncMock(return_value=self.allowance)
        ), patch.object(views_api, "update_allowance", AsyncMock()) as save:
            response = await self.client.put(
                "/api/v1/allowance/test",
                json={"revision": 0, "lightning_address": "user@[x"},
            )
            self.assertEqual(response.status_code, 422)
            save.assert_not_awaited()

    def test_create_rejects_unknown_timezone(self):
        with self.assertRaises(ValidationError):
            AllowanceCreateRequest(
                name="Test",
                amount=1,
                lightning_address="user@example.invalid",
                start_datetime="2090-01-01T00:00:00Z",
                timezone_name="Invalid/Zone",
            )
