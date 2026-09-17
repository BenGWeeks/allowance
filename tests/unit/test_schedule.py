import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from lnbits.extensions.allowance import tasks
from lnbits.extensions.allowance.models import Allowance
from lnbits.extensions.allowance.schedule import next_occurrence


def dt(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class RecurrenceTests(unittest.TestCase):
    def test_delays_do_not_accumulate(self):
        start = dt("2026-01-15T09:00:00")
        after = start
        for month in range(2, 13):
            after = next_occurrence(start, "monthly", after + timedelta(seconds=53))
            self.assertEqual(after, dt(f"2026-{month:02d}-15T09:00:00"))

    def test_month_end_and_leap_year(self):
        for year, feb_day in [(2024, 29), (2025, 28)]:
            start = dt(f"{year}-01-31T09:00:00")
            feb = next_occurrence(start, "monthly", start)
            self.assertEqual(feb, dt(f"{year}-02-{feb_day}T09:00:00"))
            self.assertEqual(
                next_occurrence(start, "monthly", feb), dt(f"{year}-03-31T09:00:00")
            )

    def test_yearly_returns_to_leap_day(self):
        start = dt("2024-02-29T09:00:00")
        after = start
        for year in range(2025, 2029):
            after = next_occurrence(start, "yearly", after)
            day = 29 if year == 2028 else 28
            self.assertEqual(after, dt(f"{year}-02-{day}T09:00:00"))

    def test_fixed_intervals_skip_missed_periods(self):
        start = dt("2020-01-01T09:00:00")
        for frequency, seconds in [
            ("minutely", 60),
            ("hourly", 3600),
            ("daily", 86400),
            ("weekly", 604800),
        ]:
            with self.subTest(frequency=frequency):
                interval = timedelta(seconds=seconds)
                after = start + interval * 10000 + timedelta(seconds=7)
                self.assertEqual(
                    next_occurrence(start, frequency, after), start + interval * 10001
                )

    def test_monthly_downtime_skips_arrears(self):
        self.assertEqual(
            next_occurrence(
                dt("2020-01-31T09:00:00"), "monthly", dt("2026-05-12T14:00:00")
            ),
            dt("2026-05-31T09:00:00"),
        )

    def test_future_start_and_naive_legacy_dates(self):
        start = datetime(2026, 1, 31, 9)
        self.assertEqual(
            next_occurrence(start, "monthly", datetime(2026, 1, 1)),
            start.replace(tzinfo=timezone.utc),
        )

    def test_offset_is_normalized_to_utc(self):
        start = datetime.fromisoformat("2026-01-01T10:00:00+01:00")
        self.assertEqual(
            next_occurrence(start, "daily", start), dt("2026-01-02T09:00:00")
        )

    def test_once_has_no_recurrence(self):
        start = dt("2026-01-01")
        self.assertEqual(
            next_occurrence(start, "once", start - timedelta(seconds=1)), start
        )
        self.assertIsNone(next_occurrence(start, "once", start))

    def test_unsupported_frequency_rejected(self):
        with self.assertRaises(ValueError):
            next_occurrence(dt("2026-01-01"), "invalid", dt("2026-01-01"))


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_once_attempt_is_terminal(self):
        for success in [True, False]:
            allowance = Allowance(
                id="once-test",
                name="Once",
                wallet="wallet",
                lightning_address="recipient@example.invalid",
                amount=1,
                start_datetime=dt("2020-01-01"),
                next_payment_date=dt("2020-01-01"),
                frequency_type="once",
            )
            with patch.object(
                tasks,
                "get_all_active_allowances",
                AsyncMock(side_effect=[[allowance], []]),
            ), patch.object(
                tasks,
                "execute_lightning_address_payment",
                AsyncMock(return_value=success),
            ) as pay, patch.object(
                tasks, "finish_payment_attempt", AsyncMock()
            ) as stop, patch.object(
                tasks, "update_allowance_error", AsyncMock()
            ) as advance, patch.object(
                tasks.asyncio,
                "sleep",
                AsyncMock(side_effect=[None, tasks.asyncio.CancelledError]),
            ):
                with self.assertRaises(tasks.asyncio.CancelledError):
                    await tasks.check_and_process_allowances()
                pay.assert_awaited_once()
                stop.assert_awaited_once_with(allowance, None)
                advance.assert_not_awaited()

    async def test_success_and_failure_advance_from_original_anchor(self):
        for success in [True, False]:
            with self.subTest(success=success):
                allowance = Allowance(
                    id="schedule-test",
                    name="Schedule",
                    wallet="test-wallet",
                    lightning_address="recipient@example.invalid",
                    amount=1,
                    start_datetime=dt("2026-01-31T09:00:00"),
                    next_payment_date=dt("2026-02-28T09:00:53"),
                    frequency_type="monthly",
                )
                # Completion is a month after the poll: no immediately-due retry.
                with patch.object(tasks, "datetime") as clock, patch.object(
                    tasks,
                    "get_all_active_allowances",
                    AsyncMock(return_value=[allowance]),
                ), patch.object(
                    tasks,
                    "execute_lightning_address_payment",
                    AsyncMock(return_value=success),
                ) as pay, patch.object(
                    tasks, "finish_payment_attempt", AsyncMock()
                ) as save, patch.object(
                    tasks.asyncio,
                    "sleep",
                    AsyncMock(side_effect=tasks.asyncio.CancelledError),
                ):
                    clock.now.side_effect = [
                        dt("2026-03-01T10:00:00"),
                        dt("2026-04-01T10:00:00"),
                    ]
                    with self.assertRaises(tasks.asyncio.CancelledError):
                        await tasks.check_and_process_allowances()
                    pay.assert_awaited_once()
                    save.assert_awaited_once_with(allowance, dt("2026-04-30T09:00:00"))


class ScheduleEditTests(unittest.IsolatedAsyncioTestCase):
    async def test_edit_and_reactivation_preserve_due_date(self):
        from types import SimpleNamespace

        from lnbits.extensions.allowance import views_api

        for active, start in [
            (True, "2020-01-31"),
            (False, "2020-01-31"),
            (False, "2090-01-31"),
        ]:
            with self.subTest(active=active, start=start):
                allowance = Allowance(
                    id="edit-test",
                    name="Original",
                    wallet="wallet",
                    lightning_address="recipient@example.invalid",
                    amount=1,
                    start_datetime=dt(start),
                    next_payment_date=dt(start),
                    frequency_type="monthly",
                    active=active,
                )
                request = SimpleNamespace(
                    json=AsyncMock(return_value={"name": "Renamed", "active": True})
                )
                wallet = SimpleNamespace(id="wallet", user="owner")

                async def save(data):
                    return Allowance(**data.dict())

                with patch.object(
                    views_api, "get_allowance", AsyncMock(return_value=allowance)
                ), patch.object(
                    views_api, "update_allowance", AsyncMock(side_effect=save)
                ) as update:
                    await views_api.api_allowance_update(allowance.id, request, wallet)
                    self.assertEqual(
                        update.await_args.args[0].next_payment_date,
                        allowance.next_payment_date,
                    )


class PendingWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_pending_does_not_advance_or_deactivate(self):
        allowance = Allowance(
            id="pending",
            name="Pending",
            wallet="wallet",
            amount=1,
            lightning_address="recipient@example.invalid",
            frequency_type="once",
            start_datetime=dt("2020-01-01"),
            next_payment_date=dt("2020-01-01"),
        )
        with patch.object(
            tasks, "get_all_active_allowances", AsyncMock(return_value=[allowance])
        ), patch.object(
            tasks, "execute_lightning_address_payment", AsyncMock(return_value=None)
        ), patch.object(
            tasks, "finish_payment_attempt", AsyncMock()
        ) as finish, patch.object(
            tasks.asyncio, "sleep", AsyncMock(side_effect=tasks.asyncio.CancelledError)
        ):
            with self.assertRaises(tasks.asyncio.CancelledError):
                await tasks.check_and_process_allowances()
            finish.assert_not_awaited()
