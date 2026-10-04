"""Bounded public HTTPS requests for untrusted LNURL endpoints."""

import asyncio
import ipaddress
import json
import os
import re
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


TRUSTED_DESTINATIONS_ENV = "ALLOWANCE_TRUSTED_LNURL_DESTINATIONS"
_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)


def trusted_destinations() -> dict[str, set[str]]:
    """Read operator-owned exact hostname/IP pairs; invalid policy fails closed."""
    try:
        policy = json.loads(os.environ.get(TRUSTED_DESTINATIONS_ENV, "{}"))
        if not isinstance(policy, dict):
            raise ValueError
        result = {}
        for host, values in policy.items():
            if (
                not isinstance(host, str)
                or len(host) > 253
                or not re.fullmatch(
                    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
                    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+",
                    host,
                )
                or not isinstance(values, list)
                or not values
            ):
                raise ValueError
            addresses = set()
            for value in values:
                if not isinstance(value, str):
                    raise ValueError
                address = ipaddress.IPv4Address(value)
                if not any(address in network for network in _PRIVATE_NETWORKS):
                    raise ValueError
                addresses.add(str(address))
            result[host] = addresses
        return result
    except (ValueError, TypeError):
        raise ValueError("Invalid trusted LNURL destination configuration") from None


class PrivateLNURLAddressError(ValueError):
    pass


class PublicNetworkBackend(httpcore.AnyIOBackend):
    def __init__(self, deadline):
        super().__init__()
        self.deadline = deadline
        self.trusted = trusted_destinations()

    async def connect_tcp(
        self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        loop = asyncio.get_running_loop()
        deadline = (
            min(self.deadline, loop.time() + timeout)
            if timeout is not None
            else self.deadline
        )
        results = await loop.getaddrinfo(
            host, port, family=socket.AF_INET, type=socket.SOCK_STREAM
        )
        addresses = list(dict.fromkeys(result[4][0] for result in results))
        hostname = host.removesuffix(".").lower()
        approved = self.trusted.get(hostname, set()) if port == 443 else set()
        if not addresses or not all(
            public_address(address) or address in approved for address in addresses
        ):
            raise PrivateLNURLAddressError(
                "LNURL host must resolve only to public addresses"
            )
        for index, address in enumerate(addresses):
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise httpcore.ConnectTimeout("LNURL connection deadline expired")
            # Reserve a share for each remaining address and for TLS/response I/O.
            attempt_timeout = remaining / (len(addresses) - index + 1)
            try:
                # Connect to the validated IP, not the hostname: a second DNS
                # resolution must not rebind the connection to a private host.
                # HTTPcore retains the original host for Host and TLS SNI/cert checks.
                return await asyncio.wait_for(
                    super().connect_tcp(
                        address, port, attempt_timeout, local_address, socket_options
                    ),
                    timeout=attempt_timeout,
                )
            except (
                OSError,
                httpcore.ConnectError,
                httpcore.ConnectTimeout,
                asyncio.TimeoutError,
            ):
                continue
        raise httpcore.ConnectError("Could not connect to LNURL host")


async def _get_json(url: httpx.URL, deadline: float) -> dict:
    async with httpcore.AsyncConnectionPool(
        ssl_context=ssl.create_default_context(),
        network_backend=PublicNetworkBackend(deadline),
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
    deadline = asyncio.get_running_loop().time() + REQUEST_TIMEOUT
    return await asyncio.wait_for(_get_json(target, deadline), timeout=REQUEST_TIMEOUT)
