import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI
from lnbits.extensions.allowance import crud, views_api


class AuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.wallet = SimpleNamespace(
            id="owned-wallet",
            user="owner",
            name="Wallet",
            adminkey="must-not-leak-admin",
            inkey="must-not-leak-invoice",
        )
        self.user = SimpleNamespace(super_user=False, wallets=[self.wallet])
        app = FastAPI()
        app.include_router(views_api.allowance_api_router)
        app.dependency_overrides[views_api.require_invoice_key] = lambda: self.wallet
        app.dependency_overrides[views_api.require_admin_key] = lambda: self.wallet
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_invoice_key_cannot_obtain_wallet_secrets(self):
        response = await self.client.get("/api/v1/wallet-info")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": self.wallet.id, "name": "Wallet"})
        self.assertNotIn(self.wallet.adminkey, response.text)
        self.assertNotIn(self.wallet.inkey, response.text)

    async def test_non_superuser_cannot_list_other_users(self):
        with patch.object(
            views_api, "get_user", AsyncMock(return_value=self.user)
        ), patch.object(views_api, "get_all_active_allowances", AsyncMock()) as read:
            response = await self.client.get("/api/v1/allowance?all_wallets=true")
            self.assertEqual(response.status_code, 403)
            read.assert_not_awaited()

    async def test_normal_listing_is_scoped_to_users_wallets(self):
        with patch.object(
            views_api, "get_user", AsyncMock(return_value=self.user)
        ), patch.object(
            views_api, "get_allowances", AsyncMock(return_value=[])
        ) as read:
            response = await self.client.get("/api/v1/allowance")
            self.assertEqual(response.status_code, 200)
            read.assert_awaited_once_with([self.wallet.id])

    async def test_superuser_can_explicitly_list_all(self):
        self.user.super_user = True
        with patch.object(
            views_api, "get_user", AsyncMock(return_value=self.user)
        ), patch.object(
            views_api, "get_all_active_allowances", AsyncMock(return_value=[])
        ) as read:
            response = await self.client.get("/api/v1/allowance?all_wallets=true")
            self.assertEqual(response.status_code, 200)
            read.assert_awaited_once()

    async def test_scheduler_diagnostics_do_not_leak_other_users_counts(self):
        other = SimpleNamespace(wallet="another-users-wallet")
        with patch.object(
            views_api, "get_all_active_allowances", AsyncMock(return_value=[other])
        ):
            response = await self.client.post("/api/v1/allowance/test-scheduler")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["total_active_allowances"], 0)

    async def test_other_wallet_cannot_read_allowance(self):
        with patch.object(
            views_api,
            "get_allowance",
            AsyncMock(return_value=SimpleNamespace(wallet="other")),
        ):
            response = await self.client.get("/api/v1/allowance/private")
            self.assertEqual(response.status_code, 403)


class QueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_wallet_id_is_bound_as_data(self):
        malicious = "x') OR 1=1 --"
        with patch.object(crud.db, "fetchall", AsyncMock(return_value=[])) as read:
            await crud.get_allowances([malicious])
            query, values = read.await_args.args
            self.assertNotIn(malicious, query)
            self.assertEqual(values, {"wallet_0": malicious})

    async def test_empty_wallet_list_does_not_query(self):
        with patch.object(crud.db, "fetchall", AsyncMock()) as read:
            self.assertEqual(await crud.get_allowances([]), [])
            read.assert_not_awaited()
