#!/usr/bin/env python3
"""Read-only health check for cron or an external uptime monitor. Exit 0/2."""

import json
import os
import sys
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, "Redirect rejected", headers, fp)


def main():
    try:
        base = os.environ["ALLOWANCE_URL"].rstrip("/")
        key = os.environ["ALLOWANCE_INVOICE_KEY"]
        url = urlsplit(base)
        local = url.hostname in ("localhost", "127.0.0.1", "::1")
        if (
            (url.scheme != "https" and not (url.scheme == "http" and local))
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Invalid monitor URL")
        request = Request(base + "/allowance/api/v1/health", headers={"X-Api-Key": key})
        with build_opener(NoRedirect).open(request, timeout=10) as response:
            data = json.loads(response.read(16384))
        if not isinstance(data, dict) or type(data.get("healthy")) is not bool:
            raise ValueError("Invalid health response")
        # Never print response bodies, URLs, keys, or exception details.
        print(
            json.dumps(
                {
                    "healthy": data["healthy"],
                    "scheduler_ok": data.get("scheduler_ok") is True,
                    "overdue": data.get("overdue"),
                    "pending": data.get("pending"),
                }
            )
        )
        return 0 if data["healthy"] else 2
    except Exception:
        print(
            '{"healthy": false, '
            '"error": "Allowance unavailable, disabled, or health check failed"}'
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
