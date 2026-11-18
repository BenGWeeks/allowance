"""Eligibility and atomic scheduling for explicitly requested occurrence retries."""

import json
from datetime import datetime, timedelta, timezone

from .models import Allowance


def payment_snapshot(allowance: Allowance) -> str:
    return json.dumps(
        {
            key: getattr(allowance, key)
            for key in ("amount", "currency", "lightning_address", "memo")
        },
        sort_keys=True,
    )


def retry_block_reason(allowance, occurrence, now):
    if allowance.pending_payment_hash:
        return "A payment is awaiting confirmation. Check its status first."
    if not allowance.active:
        return "This allowance is paused or finished."
    if allowance.end_datetime and allowance.end_datetime <= now:
        return "This allowance has ended."
    if allowance.retry_resume_date:
        return "An earlier payment is already being retried."
    due = int(allowance.next_payment_date.timestamp())
    if occurrence["scheduled_at"] == due and occurrence.get("current"):
        if not allowance.retry_after or not allowance.retry_deadline:
            return "There is no confirmed-unsent failure eligible for retry."
        if allowance.retry_deadline <= now:
            return "Automatic retries have ended; refresh after this occurrence closes."
        if allowance.retry_after <= now:
            return "An attempt is already queued."
        return None
    return historical_retry_block_reason(allowance, occurrence, now)


def historical_retry_block_reason(allowance, occurrence, now):
    if occurrence.get("outcome") not in {"failed", "skipped"}:
        return "Only failed or skipped occurrences can be paid."
    if occurrence["scheduled_at"] >= int(now.timestamp()):
        return "This occurrence is not yet due."
    if occurrence.get("payment_hash"):
        return (
            "This payment was submitted. Operator verification is required "
            "before resending."
        )
    if not occurrence.get("retry_snapshot"):
        return (
            "This older occurrence has no saved payment details "
            "to verify a safe payment."
        )
    if occurrence["retry_snapshot"] != payment_snapshot(allowance):
        return "Payment details have changed since this occurrence."
    if allowance.next_payment_date <= now or allowance.retry_after:
        return "The current scheduled payment must finish first."
    return None


async def request_retry(allowance, occurrence, revision):
    from .crud import AllowanceConflictError, _append_payment_log, db, transaction

    now = datetime.now(timezone.utc)
    reason = retry_block_reason(allowance, occurrence, now)
    if reason or revision != allowance.revision:
        raise AllowanceConflictError(
            reason or "Allowance changed. Refresh and try again."
        )
    skipped = occurrence.get("outcome") == "skipped"
    historical = not occurrence.get("current")
    due = occurrence["scheduled_at"]
    deadline = (
        min(now + timedelta(hours=24), allowance.next_payment_date)
        if historical
        else allowance.retry_deadline
    )
    resume = int(allowance.next_payment_date.timestamp()) if historical else None
    async with transaction(db) as conn:
        result = await conn.execute(
            f"UPDATE {db.references_schema}maintable SET "
            f"next_payment_date = {db.timestamp_placeholder('due')}, "
            f"retry_after = {db.timestamp_placeholder('now')}, "
            f"retry_deadline = {db.timestamp_placeholder('deadline')}, "
            f"retry_resume_date = {db.timestamp_placeholder('resume')}, "
            "revision = revision + 1 WHERE id = :id AND revision = :revision "
            "AND pending_payment_hash IS NULL AND retry_resume_date IS NULL "
            "AND active = true",
            {
                "id": allowance.id,
                "revision": revision,
                "due": due,
                "now": int(now.timestamp()),
                "deadline": int(deadline.timestamp()),
                "resume": resume,
            },
        )
        if result.rowcount != 1:
            raise AllowanceConflictError(
                "Payment state changed. Refresh and try again."
            )
        attempted = allowance.model_copy(
            update={"next_payment_date": datetime.fromtimestamp(due, timezone.utc)}
        )
        await _append_payment_log(
            conn,
            attempted,
            "payment_request" if skipped else "retry",
            "manual_skipped_payment_requested" if skipped else "manual_retry_requested",
            (
                "User requested payment of this skipped occurrence."
                if skipped
                else "User requested a retry of this scheduled payment."
            ),
            int(now.timestamp()),
        )


async def cancel_retry(allowance, revision, scheduled_at):
    """End an explicitly requested occurrence retry without sending anything.

    The occurrence keeps its recorded failed or skipped outcome and the regular
    schedule resumes, which makes the payment details editable again.
    """
    from .crud import AllowanceConflictError, _append_payment_log, db, transaction
    from .schedule import next_occurrence

    if allowance.pending_payment_hash:
        raise AllowanceConflictError(
            "A payment is awaiting confirmation. Check its status first."
        )
    if not allowance.retry_resume_date:
        raise AllowanceConflictError("There is no requested retry to cancel.")
    if revision != allowance.revision or scheduled_at != int(
        allowance.next_payment_date.timestamp()
    ):
        raise AllowanceConflictError("Allowance changed. Refresh and try again.")
    now = datetime.now(timezone.utc)
    next_date = allowance.retry_resume_date
    if next_date <= now:
        next_date = next_occurrence(
            allowance.start_datetime,
            allowance.frequency_type,
            now,
            allowance.timezone_name,
        )
    values = {"id": allowance.id, "revision": revision, "due": scheduled_at}
    if next_date is None:
        assignment = "active = false"
    else:
        assignment = f"next_payment_date = {db.timestamp_placeholder('next')}"
        values["next"] = int(next_date.timestamp())
        if allowance.end_datetime and allowance.end_datetime <= now:
            assignment += ", active = false"
    async with transaction(db) as conn:
        result = await conn.execute(
            f"UPDATE {db.references_schema}maintable SET {assignment}, "
            "retry_count = 0, retry_after = NULL, retry_deadline = NULL, "
            "retry_resume_date = NULL, revision = revision + 1 "
            "WHERE id = :id AND revision = :revision "
            "AND pending_payment_hash IS NULL AND retry_resume_date IS NOT NULL "
            f"AND next_payment_date = {db.timestamp_placeholder('due')}",
            values,
        )
        if result.rowcount != 1:
            raise AllowanceConflictError(
                "Payment state changed. Refresh and try again."
            )
        await _append_payment_log(
            conn,
            allowance,
            "retry",
            "manual_retry_cancelled",
            "User cancelled the requested retry. Nothing was sent.",
        )
