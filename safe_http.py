"""Bounded public HTTPS requests for untrusted LNURL endpoints."""

import asyncio
import ipaddress
import json
import socket
import ssl

import httpcore
import httpx

MAX_RESPONSE_BYTES = 256 * 1024
REQUEST_TIMEOUT = 10


def validate_url(value: str) -> httpx.URL:
    url = httpx.URL(value)
    if (
        url.scheme != "https"
        or not url.host
        or url.port not in (None, 443)
        or url.userinfo
        or url.fragment
    ):
        raise ValueError("LNURL requires a public HTTPS URL on port 443")
    return url


def public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    # IPv4-only egress avoids host-specific NAT64 prefixes translating a
    # globally scoped IPv6 destination into an internal IPv4 connection.
    return (
        isinstance(address, ipaddress.IPv4Address)
        and address.is_global
        and not address.is_multicast
        and not address.is_reserved
    )


class PublicNetworkBackend(httpcore.AnyIOBackend):
    async def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        results = await asyncio.get_running_loop().getaddrinfo(
            host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        addresses = list(dict.fromkeys(result[4][0] for result in results))
        if not addresses or not all(public_address(address) for address in addresses):
            raise ValueError("LNURL host must resolve only to public addresses")
        for address in addresses:
            try:
                # Connect to the validated IP, not the hostname: a second DNS
                # resolution must not rebind the connection to a private host.
                # HTTPcore retains the original host for Host and TLS SNI/cert checks.
                return await super().connect_tcp(
                    address, port, timeout, local_address, socket_options
                )
            except (OSError, httpcore.ConnectError):
                continue
        raise httpcore.ConnectError("Could not connect to LNURL host")


async def _get_json(url: httpx.URL) -> dict:
    async with httpcore.AsyncConnectionPool(
        ssl_context=ssl.create_default_context(),
        network_backend=PublicNetworkBackend(),
        max_connections=1,
        max_keepalive_connections=0,
    ) as pool:
        async with pool.stream(
            "GET",
            str(url),
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
            extensions={
                "timeout": {
                    "connect": REQUEST_TIMEOUT,
                    "read": REQUEST_TIMEOUT,
                    "write": REQUEST_TIMEOUT,
                    "pool": REQUEST_TIMEOUT,
                }
            },
        ) as response:
            if response.status != 200:
                raise ValueError("LNURL endpoint returned an unsuccessful status")
            content = bytearray()
            async for chunk in response.aiter_stream():
                if len(content) + len(chunk) > MAX_RESPONSE_BYTES:
                    raise ValueError("LNURL response is too large")
                content.extend(chunk)
    result = json.loads(content)
    if not isinstance(result, dict):
        raise ValueError("LNURL endpoint must return a JSON object")
    return result


async def get_public_json(url: str, params=None) -> dict:
    target = validate_url(url)
    if params:
        target = target.copy_merge_params(params)
    # Includes DNS, connect, TLS, streaming, and all fallback addresses in one budget.
    return await asyncio.wait_for(_get_json(target), timeout=REQUEST_TIMEOUT)
