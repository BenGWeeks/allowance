import asyncio
import json
import socket
import ssl
import unittest
from unittest.mock import AsyncMock, patch

import httpcore
from lnbits.extensions.allowance import safe_http, tasks


class Stream(httpcore.AsyncNetworkStream):
    def __init__(self, body, status=200):
        self.data = (
            f"HTTP/1.1 {status} Test\r\nContent-Length: {len(body)}\r\n\r\n".encode()
            + body
        )
        self.written = b""
        self.hostname = None

    async def read(self, max_bytes, timeout=None):
        result, self.data = self.data[:max_bytes], self.data[max_bytes:]
        return result

    async def write(self, buffer, timeout=None):
        self.written += buffer

    async def aclose(self):
        pass

    async def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        assert ssl_context.verify_mode == ssl.CERT_REQUIRED
        assert ssl_context.check_hostname
        self.hostname = server_hostname
        return self

    def get_extra_info(self, info):
        return None


class NetworkTests(unittest.IsolatedAsyncioTestCase):
    async def test_private_mixed_and_translated_addresses_never_connect(self):
        for blocked in [
            "127.0.0.1",
            "10.0.0.1",
            "169.254.169.254",
            "::1",
            "fc00::1",
            "::ffff:127.0.0.1",
            "64:ff9b::7f00:1",
            "224.0.0.1",
            "2001:4860:64::7f00:1",
            "2606:4700:4700::1111",
        ]:
            results = [
                (socket.AF_INET, 1, 6, "", (ip, 443)) for ip in ["8.8.8.8", blocked]
            ]
            with patch.object(
                asyncio.get_running_loop(),
                "getaddrinfo",
                AsyncMock(return_value=results),
            ), patch.object(
                httpcore.AnyIOBackend, "connect_tcp", AsyncMock()
            ) as connect:
                with self.assertRaises(ValueError):
                    await safe_http.get_public_json("https://recipient.example/pay")
                connect.assert_not_awaited()

    async def test_transport_pins_ip_and_preserves_tls_and_host(self):
        stream = Stream(json.dumps({"ok": True}).encode())
        results = [(socket.AF_INET, 1, 6, "", ("8.8.8.8", 443))]
        with patch.object(
            asyncio.get_running_loop(), "getaddrinfo", AsyncMock(return_value=results)
        ) as dns, patch.object(
            httpcore.AnyIOBackend, "connect_tcp", AsyncMock(return_value=stream)
        ) as connect:
            result = await safe_http.get_public_json("https://recipient.example/pay")
        self.assertEqual(result, {"ok": True})
        dns.assert_awaited_once()
        self.assertEqual(dns.await_args.kwargs["family"], socket.AF_INET)
        self.assertEqual(connect.await_args.args[0], "8.8.8.8")
        self.assertEqual(stream.hostname, "recipient.example")
        self.assertIn(b"Host: recipient.example", stream.written)

    async def test_redirects_and_large_responses_are_rejected(self):
        for stream in [
            Stream(b"{}", 302),
            Stream(b" " * (safe_http.MAX_RESPONSE_BYTES + 1)),
        ]:
            with patch.object(
                safe_http.PublicNetworkBackend,
                "connect_tcp",
                AsyncMock(return_value=stream),
            ) as connect:
                with self.assertRaises(ValueError):
                    await safe_http.get_public_json("https://recipient.example/pay")
                connect.assert_awaited_once()

    def test_unsafe_urls_are_rejected(self):
        for url in [
            "http://example.com",
            "https://user:secret@example.com",
            "https://example.com:5000",
            "https://example.com/#fragment",
            "file:///etc/passwd",
        ]:
            with self.assertRaises(ValueError):
                safe_http.validate_url(url)

    async def test_callback_and_payrequest_validation(self):
        valid = {
            "tag": "payRequest",
            "minSendable": 1000,
            "maxSendable": 2000,
            "metadata": '[["text/plain","Test"]]',
            "callback": "https://example.com/pay",
        }
        for change in [
            {"callback": "http://127.0.0.1"},
            {"minSendable": 3000},
            {"tag": "withdrawRequest"},
            {"commentAllowed": -1},
        ]:
            with patch.object(
                tasks, "get_public_json", AsyncMock(return_value={**valid, **change})
            ):
                with self.assertRaises(ValueError):
                    await tasks.resolve_lightning_address("user@example.com")

    async def test_stalled_first_address_does_not_prevent_fallback(self):
        stream = Stream(b'{"ok":true}')
        addresses = ["8.8.8.8", "1.1.1.1"]
        results = [(socket.AF_INET, 1, 6, "", (ip, 443)) for ip in addresses]
        attempted = []
        cancelled = asyncio.Event()

        async def connect(host, port, timeout, local_address, socket_options):
            attempted.append((host, timeout))
            if host == addresses[0]:
                try:
                    await asyncio.Future()
                finally:
                    cancelled.set()
            return stream

        with patch.object(
            asyncio.get_running_loop(), "getaddrinfo", AsyncMock(return_value=results)
        ), patch.object(
            httpcore.AnyIOBackend, "connect_tcp", AsyncMock(side_effect=connect)
        ), patch.object(
            safe_http, "REQUEST_TIMEOUT", 0.6
        ):
            result = await safe_http.get_public_json("https://recipient.example/pay")
        self.assertEqual(result, {"ok": True})
        self.assertTrue(cancelled.is_set())
        self.assertEqual([host for host, _ in attempted], addresses)
        self.assertTrue(all(0 < timeout < 0.6 for _, timeout in attempted))
        self.assertEqual(stream.hostname, "recipient.example")

    async def test_connect_timeout_tries_next_validated_address(self):
        results = [
            (socket.AF_INET, 1, 6, "", (ip, 443)) for ip in ("8.8.8.8", "1.1.1.1")
        ]
        with patch.object(
            asyncio.get_running_loop(), "getaddrinfo", AsyncMock(return_value=results)
        ), patch.object(
            httpcore.AnyIOBackend,
            "connect_tcp",
            AsyncMock(side_effect=[httpcore.ConnectTimeout(), Stream(b"{}")]),
        ) as connect:
            self.assertEqual(
                await safe_http.get_public_json("https://recipient.example/pay"), {}
            )
        self.assertEqual(connect.await_count, 2)

    async def test_lightning_username_starting_with_lnurl_is_not_decoded(self):
        data = {
            "tag": "payRequest",
            "minSendable": 1000,
            "maxSendable": 2000,
            "metadata": '[["text/plain","Test"]]',
            "callback": "https://example.com/pay",
        }
        for username in ("lnurluser", "LNURLuser"):
            with patch.object(
                tasks, "get_public_json", AsyncMock(return_value=data)
            ) as fetch, patch.object(tasks, "lnurl_decode") as decode:
                callback, result = await tasks.resolve_lightning_address(
                    f"{username}@example.com"
                )
                self.assertEqual(callback, data["callback"])
                self.assertEqual(result, data)
                fetch.assert_awaited_once_with(
                    f"https://example.com/.well-known/lnurlp/{username}"
                )
                decode.assert_not_called()
