import importlib.util
import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location(
    "allowance_monitor",
    Path(__file__).resolve().parents[2] / "scripts" / "check_allowance_health.py",
)
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def test_healthy_and_unhealthy_exit_codes(self):
        for healthy, expected in [(b"true", 0), (b"false", 2)]:
            response = MagicMock()
            response.__enter__.return_value.read.return_value = (
                b'{"healthy":'
                + healthy
                + b',"scheduler_ok":true,"overdue":0,"pending":0}'
            )
            with patch.dict(
                monitor.os.environ,
                {
                    "ALLOWANCE_URL": "https://example.invalid",
                    "ALLOWANCE_INVOICE_KEY": "SECRET",
                },
            ), patch.object(monitor, "build_opener") as opener, redirect_stdout(
                io.StringIO()
            ) as output:
                opener.return_value.open.return_value = response
                self.assertEqual(monitor.main(), expected)
                self.assertNotIn("SECRET", output.getvalue())

    def test_unavailable_monitor_never_prints_exception_details(self):
        with patch.dict(
            monitor.os.environ,
            {
                "ALLOWANCE_URL": "https://example.invalid",
                "ALLOWANCE_INVOICE_KEY": "SECRET",
            },
        ), patch.object(
            monitor, "build_opener", side_effect=RuntimeError("SECRET")
        ), redirect_stdout(
            io.StringIO()
        ) as output:
            self.assertEqual(monitor.main(), 2)
            self.assertNotIn("SECRET", output.getvalue())
